import Foundation
import Hummingbird
import Inference
import NIOCore

// Usage: serve <model-directory> [--name id] [--port 8080] [--bits 4|8|16] [--no-mtp] [--batch N]
let args = CommandLine.arguments
func option(_ name: String) -> String? {
    args.firstIndex(of: name).flatMap { args.indices.contains($0 + 1) ? args[$0 + 1] : nil }
}
let directory = URL(filePath: args[1])
let port = Int(option("--port") ?? "") ?? 8080
let batchSize = Int(option("--batch") ?? "") ?? 1

let bits = Int(option("--bits") ?? "") ?? 4
let loaded = try await LoadedModel.load(directory: directory, name: option("--name"), quantizeBits: bits == 16 ? nil : bits)
let engine: any InferenceEngine = batchSize > 1
    ? BatchEngine(loaded: loaded, maxBatch: batchSize)
    : SerialEngine(loaded: loaded, useMTP: !args.contains("--no-mtp"))
let modelName = loaded.name
let formatter = PromptFormatter(loaded)
let metrics = Metrics()
print("loaded \(modelName), listening on 127.0.0.1:\(port)")

let router = Router()

router.get("health") { _, _ in "ok" }

router.get("metrics") { _, _ in metrics.render() }

router.get("v1/models") { _, _ in
    try json(ModelList(data: [.init(id: modelName)]))
}

router.post("v1/chat/completions") { request, context -> Response in
    let body = try await request.body.collect(upTo: 4 << 20)
    let chat: ChatRequest
    let messages: [[String: Any]]
    let tools: [[String: Any]]?
    do {
        chat = try jsonDecoder.decode(ChatRequest.self, from: body)
        let raw = try JSONSerialization.jsonObject(with: Data(buffer: body)) as? [String: Any] ?? [:]
        guard let m = raw["messages"] as? [[String: Any]], !m.isEmpty else { throw ServeError.noMessages }
        messages = m
        tools = raw["tools"] as? [[String: Any]]
    } catch {
        return try json(ErrorBody(error: .init(message: "\(error)", type: "invalid_request_error")), status: .badRequest)
    }

    let prompt = try formatter.render(
        messages: messages.map(templateMessage),
        tools: tools?.map { $0.mapValues(sendableJSON) },
        enableThinking: chat.enableThinking ?? false)
    let expectTools = !(tools ?? []).isEmpty
    let generation = GenerationRequest(
        prompt: prompt,
        parameters: SamplingParameters(
            temperature: chat.temperature ?? 0.7, topK: chat.topK ?? 0, topP: chat.topP ?? 1,
            minP: chat.minP ?? 0, seed: chat.seed),
        maxTokens: chat.maxCompletionTokens ?? chat.maxTokens ?? 512,
        stop: chat.stop?.list ?? [])

    let submitted: AsyncThrowingStream<GenerationEvent, Error>
    do {
        submitted = try engine.submit(generation)
    } catch EngineError.queueFull {
        metrics.update { $0.rejected += 1 }
        return try json(ErrorBody(error: .init(message: "server busy, retry later", type: "rate_limit")), status: .tooManyRequests)
    }

    let id = "chatcmpl-" + UUID().uuidString.prefix(12).lowercased()
    let created = Int(Date().timeIntervalSince1970)
    let events = instrument(submitted)

    if chat.stream == true {
        return Response(
            status: .ok,
            headers: [.contentType: "text/event-stream", .cacheControl: "no-cache"],
            body: ResponseBody { writer in
                func send(_ chunk: ChatChunk) async throws {
                    let data = try jsonEncoder.encode(chunk)
                    try await writer.write(ByteBuffer(string: "data: " + String(decoding: data, as: UTF8.self) + "\n\n"))
                }
                try await send(ChatChunk(id: id, created: created, model: modelName,
                                         choices: [.init(delta: .init(role: "assistant"))]))
                // Text streams through until a tool call starts. From there it
                // is buffered and sent as one structured delta at the end.
                var buffered = ""
                // If the client disconnects, the write throws, this loop ends,
                // and the stream's onTermination cancels the job in the engine.
                for try await event in events {
                    switch event {
                    case .text(let text):
                        if expectTools && (!buffered.isEmpty || text.contains("<")) {
                            buffered += text
                            // Release text once it is clearly not the start of a call.
                            if !buffered.contains(ToolCallParser.openTag)
                                && !ToolCallParser.openTag.hasPrefix(buffered.suffix(from: buffered.lastIndex(of: "<") ?? buffered.startIndex)) {
                                try await send(ChatChunk(id: id, created: created, model: modelName,
                                                         choices: [.init(delta: .init(content: buffered))]))
                                buffered = ""
                            }
                        } else {
                            try await send(ChatChunk(id: id, created: created, model: modelName,
                                                     choices: [.init(delta: .init(content: text))]))
                        }
                    case .finished(let reason, let usage):
                        let (content, calls) = ToolCallParser.parse(buffered)
                        if !calls.isEmpty {
                            try await send(ChatChunk(id: id, created: created, model: modelName,
                                                     choices: [.init(delta: .init(content: content.isEmpty ? nil : content,
                                                                                  toolCalls: toolCallBodies(calls)))]))
                        } else if !buffered.isEmpty {
                            try await send(ChatChunk(id: id, created: created, model: modelName,
                                                     choices: [.init(delta: .init(content: buffered))]))
                        }
                        try await send(ChatChunk(id: id, created: created, model: modelName,
                                                 choices: [.init(delta: .init(),
                                                                 finishReason: calls.isEmpty ? reason.rawValue : "tool_calls")],
                                                 usage: usageBody(usage)))
                    }
                }
                try await writer.write(ByteBuffer(string: "data: [DONE]\n\n"))
                try await writer.finish(nil)
            })
    }

    var text = ""
    var finish = FinishReason.length
    var usage = Usage(promptTokens: 0, completionTokens: 0, cachedTokens: 0)
    for try await event in events {
        switch event {
        case .text(let t): text += t
        case .finished(let r, let u): finish = r; usage = u
        }
    }
    let (content, calls) = expectTools ? ToolCallParser.parse(text) : (text, [])
    return try json(ChatCompletion(
        id: id, created: created, model: modelName,
        choices: [.init(
            message: .init(role: "assistant", content: calls.isEmpty ? text : content,
                           toolCalls: calls.isEmpty ? nil : toolCallBodies(calls)),
            finishReason: calls.isEmpty ? finish.rawValue : "tool_calls")],
        usage: usageBody(usage)))
}

enum ServeError: Error {
    case noMessages
}

func toolCallBodies(_ calls: [ToolCall]) -> [ToolCallBody] {
    calls.enumerated().map { i, call in
        ToolCallBody(index: i, id: "call_" + UUID().uuidString.prefix(8).lowercased(),
                     function: .init(name: call.name, arguments: call.arguments))
    }
}

/// Wraps an event stream to record request metrics as events pass through.
func instrument(_ events: AsyncThrowingStream<GenerationEvent, Error>) -> AsyncThrowingStream<GenerationEvent, Error> {
    metrics.update { $0.requests += 1; $0.inFlight += 1 }
    let start = Date()
    return AsyncThrowingStream { continuation in
        let task = Task {
            var first: Date?
            var finished = false
            do {
                for try await event in events {
                    if first == nil, case .text = event {
                        first = Date()
                        let ttft = first!.timeIntervalSince(start)
                        metrics.update { $0.timeToFirstTokenSum += ttft; $0.timeToFirstTokenCount += 1 }
                    }
                    if case .finished(let reason, let usage) = event {
                        finished = true
                        let decode = first.map { Date().timeIntervalSince($0) } ?? 0
                        metrics.update {
                            $0.promptTokens += usage.promptTokens
                            $0.cachedPromptTokens += usage.cachedTokens
                            $0.completionTokens += usage.completionTokens
                            $0.decodeSecondsSum += decode
                            if reason == .cancelled { $0.cancelled += 1 }
                        }
                    }
                    continuation.yield(event)
                }
                continuation.finish()
            } catch {
                continuation.finish(throwing: error)
            }
            // A client that disconnects never sees the finished event.
            let sawFinish = finished
            metrics.update {
                $0.inFlight -= 1
                if !sawFinish { $0.cancelled += 1 }
            }
        }
        continuation.onTermination = { _ in task.cancel() }
    }
}

func usageBody(_ u: Usage) -> UsageBody {
    UsageBody(promptTokens: u.promptTokens, completionTokens: u.completionTokens,
              totalTokens: u.promptTokens + u.completionTokens,
              promptTokensDetails: .init(cachedTokens: u.cachedTokens))
}

func json(_ value: some Encodable, status: HTTPResponse.Status = .ok) throws -> Response {
    Response(status: status, headers: [.contentType: "application/json"],
             body: ResponseBody(byteBuffer: ByteBuffer(data: try jsonEncoder.encode(value))))
}

let app = Application(router: router, configuration: .init(address: .hostname("127.0.0.1", port: port)))
try await app.runService()
