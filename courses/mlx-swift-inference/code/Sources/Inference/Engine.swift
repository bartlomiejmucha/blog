import Foundation
import MLX
import os

public struct GenerationRequest: Sendable {
    public var prompt: [Int]
    public var parameters: SamplingParameters
    public var maxTokens: Int
    public var stop: [String]

    public init(prompt: [Int], parameters: SamplingParameters, maxTokens: Int, stop: [String] = []) {
        self.prompt = prompt
        self.parameters = parameters
        self.maxTokens = maxTokens
        self.stop = stop
    }
}

public enum FinishReason: String, Sendable {
    case stop
    case length
    case cancelled
}

public struct Usage: Sendable {
    public var promptTokens: Int
    public var completionTokens: Int
    public var cachedTokens: Int

    public init(promptTokens: Int, completionTokens: Int, cachedTokens: Int) {
        self.promptTokens = promptTokens
        self.completionTokens = completionTokens
        self.cachedTokens = cachedTokens
    }
}

public enum GenerationEvent: Sendable {
    case text(String)
    case finished(FinishReason, Usage)
}

public enum EngineError: Error {
    case queueFull
}

/// A request waiting for, or being served by, the worker.
final class Job: Sendable {
    let request: GenerationRequest
    let continuation: AsyncThrowingStream<GenerationEvent, Error>.Continuation
    private let cancelledFlag = OSAllocatedUnfairLock(initialState: false)

    init(request: GenerationRequest, continuation: AsyncThrowingStream<GenerationEvent, Error>.Continuation) {
        self.request = request
        self.continuation = continuation
    }

    var cancelled: Bool { cancelledFlag.withLock { $0 } }
    func cancel() { cancelledFlag.withLock { $0 = true } }
}

/// Runs one request at a time on a dedicated thread.
///
/// The GPU can only do one thing at a time anyway, and MLX models are not
/// thread-safe, so all model work happens on the worker thread. Callers on
/// any thread hand requests over through a locked inbox and receive tokens
/// through an `AsyncThrowingStream`.
public final class SerialEngine: @unchecked Sendable {
    // Touched only by the worker thread.
    private let loaded: LoadedModel
    private let promptCache: PromptCache
    private let useMTP: Bool

    // Shared between threads, always behind the lock or the semaphore.
    private let inbox = OSAllocatedUnfairLock<[Job]>(initialState: [])
    private let wake = DispatchSemaphore(value: 0)
    private let maxQueue: Int

    public init(loaded: LoadedModel, maxQueue: Int = 16, useMTP: Bool = true, promptCacheEntries: Int = 4) {
        self.loaded = loaded
        self.maxQueue = maxQueue
        self.useMTP = useMTP
        self.promptCache = PromptCache(capacity: promptCacheEntries)
        let thread = Thread { [self] in self.run() }
        thread.name = "inference-worker"
        thread.stackSize = 16 << 20
        thread.start()
    }

    /// Queues a request. Throws `queueFull` instead of letting the backlog
    /// grow without bound, so the HTTP layer can answer 429 right away.
    public func submit(_ request: GenerationRequest) throws -> AsyncThrowingStream<GenerationEvent, Error> {
        let (stream, continuation) = AsyncThrowingStream.makeStream(of: GenerationEvent.self, throwing: Error.self)
        let job = Job(request: request, continuation: continuation)
        // Fires when the consumer stops listening, e.g. the client disconnects.
        continuation.onTermination = { _ in job.cancel() }
        try inbox.withLock { queue in
            guard queue.count < maxQueue else { throw EngineError.queueFull }
            queue.append(job)
        }
        wake.signal()
        return stream
    }

    public var queueDepth: Int { inbox.withLock { $0.count } }

    private func run() {
        while true {
            wake.wait()
            guard let job = inbox.withLock({ $0.isEmpty ? nil : $0.removeFirst() }) else { continue }
            if job.cancelled {
                job.continuation.finish()
                continue
            }
            serve(job)
        }
    }

    private func serve(_ job: Job) {
        let request = job.request
        var detokenizer = StreamingDetokenizer(tokenizer: loaded.tokenizer)
        var stopper = StopMatcher(stops: request.stop)
        var completion = 0
        var reason = FinishReason.length
        var hitStopString = false

        // The MTP drafter keeps its own cache, which the prompt cache does not
        // store, so MTP requests always start from scratch.
        var cached = 0
        var plain: TokenGenerator?
        var checkpoint: Int?
        var mtp: MTPGenerator?
        if useMTP, let qwen35 = loaded.model as? Qwen35Model, qwen35.mtp != nil {
            mtp = MTPGenerator(
                model: qwen35, prompt: request.prompt, parameters: request.parameters,
                maxTokens: request.maxTokens)
        } else {
            // Reuse the caches of an earlier request whose tokens are a prefix
            // of this prompt, and only prefill the rest.
            let hit = promptCache.lookup(prompt: request.prompt, model: loaded.model)
            cached = hit.count
            checkpoint = request.prompt.lastIndex(of: loaded.turnStartToken ?? -1).flatMap {
                $0 > cached ? $0 : nil
            }
            plain = TokenGenerator(
                model: loaded.model, prompt: Array(request.prompt[cached...]),
                parameters: request.parameters, maxTokens: request.maxTokens, caches: hit.caches,
                checkpoint: checkpoint.map { $0 - cached })
        }

        while let token = plain?.next() ?? mtp?.next() {
            if job.cancelled { reason = .cancelled; break }
            if loaded.eosTokens.contains(token) { reason = .stop; break }
            completion += 1
            let (text, stopped) = stopper.feed(detokenizer.append(token))
            if !text.isEmpty { job.continuation.yield(.text(text)) }
            if stopped { reason = .stop; hitStopString = true; break }
        }
        // Text held back as a possible stop-string prefix turned out not to be one.
        if !hitStopString && reason != .cancelled {
            let rest = stopper.finish()
            if !rest.isEmpty { job.continuation.yield(.text(rest)) }
        }

        if let checkpoint, let caches = plain?.checkpointCaches {
            promptCache.store(tokens: Array(request.prompt[..<checkpoint]), caches: caches)
        }
        job.continuation.yield(.finished(reason, Usage(
            promptTokens: request.prompt.count, completionTokens: completion, cachedTokens: cached)))
        job.continuation.finish()
        // Let MLX return freed buffers to the system between requests.
        MLX.Memory.clearCache()
    }
}

/// What the HTTP layer needs from an engine.
public protocol InferenceEngine: Sendable {
    func submit(_ request: GenerationRequest) throws -> AsyncThrowingStream<GenerationEvent, Error>
}

extension SerialEngine: InferenceEngine {}
