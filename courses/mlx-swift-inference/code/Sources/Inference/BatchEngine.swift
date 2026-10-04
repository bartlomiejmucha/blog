import Foundation
import MLX
import os

/// Continuous batching: many requests share each decode step.
///
/// Decoding one token is limited by reading the weights from memory, not by
/// arithmetic. Running B sequences in one step reads the weights once for
/// all of them, so throughput grows almost linearly with B until compute or
/// attention starts to dominate.
///
/// "Continuous" means the batch is not fixed: finished sequences leave and
/// waiting ones join between any two steps. New prompts are prefilled one
/// chunk per loop iteration, so a long prompt delays the running sequences
/// by at most one chunk at a time.
public final class BatchEngine: @unchecked Sendable, InferenceEngine {
    final class Sequence {
        let job: Job
        let caches: [LayerCache]
        var sampler: Sampler
        var detokenizer: StreamingDetokenizer
        var stopper: StopMatcher
        var pendingPrompt: ArraySlice<Int>
        var last = 0
        var generated = 0

        init(job: Job, loaded: LoadedModel) {
            self.job = job
            caches = loaded.model.makeCaches()
            sampler = Sampler(job.request.parameters)
            detokenizer = StreamingDetokenizer(tokenizer: loaded.tokenizer)
            stopper = StopMatcher(stops: job.request.stop)
            pendingPrompt = job.request.prompt[...]
        }
    }

    // Touched only by the worker thread.
    private let loaded: LoadedModel
    private var waiting: [Sequence] = []
    private var running: [Sequence] = []
    private let maxBatch: Int
    private let prefillChunk: Int

    // Shared with callers.
    private let inbox = OSAllocatedUnfairLock<[Job]>(initialState: [])
    private let wake = DispatchSemaphore(value: 0)
    private let maxQueue: Int

    public init(loaded: LoadedModel, maxBatch: Int = 8, maxQueue: Int = 64, prefillChunk: Int = 256) {
        self.loaded = loaded
        self.maxBatch = maxBatch
        self.maxQueue = maxQueue
        self.prefillChunk = prefillChunk
        let thread = Thread { [self] in self.run() }
        thread.name = "inference-batch-worker"
        thread.stackSize = 16 << 20
        thread.start()
    }

    public func submit(_ request: GenerationRequest) throws -> AsyncThrowingStream<GenerationEvent, Error> {
        let (stream, continuation) = AsyncThrowingStream.makeStream(of: GenerationEvent.self, throwing: Error.self)
        let job = Job(request: request, continuation: continuation)
        continuation.onTermination = { _ in job.cancel() }
        try inbox.withLock { queue in
            guard queue.count < maxQueue else { throw EngineError.queueFull }
            queue.append(job)
        }
        wake.signal()
        return stream
    }

    private func run() {
        while true {
            if waiting.isEmpty && running.isEmpty { wake.wait() }
            for job in inbox.withLock({ q in defer { q.removeAll() }; return q }) {
                waiting.append(Sequence(job: job, loaded: loaded))
            }

            // Drop sequences whose clients went away.
            for s in (waiting + running) where s.job.cancelled {
                finish(s, .cancelled)
            }

            // Admit: advance the oldest waiting prompt by one chunk.
            if running.count < maxBatch, let s = waiting.first {
                prefillChunk(s)
            }

            if !running.isEmpty {
                decodeStep()
            }
        }
    }

    private func prefillChunk(_ s: Sequence) {
        let chunk = s.pendingPrompt.prefix(prefillChunk)
        s.pendingPrompt = s.pendingPrompt.dropFirst(chunk.count)
        let logits = loaded.model(MLXArray(chunk.map(Int32.init)).reshaped(1, -1), caches: s.caches)
        if s.pendingPrompt.isEmpty {
            // The prompt is done: its last logits give the first token.
            let token = s.sampler(logits[0..., -1, 0...])
            eval(token)
            waiting.removeFirst()
            running.append(s)
            emit(s, token.item(Int.self))
        } else {
            eval(s.caches.flatMap(\.state))
        }
    }

    private func decodeStep() {
        let batch = running
        let tokens = MLXArray(batch.map { Int32($0.last) }).reshaped(batch.count, 1)

        // One cache view per layer that spans every running sequence.
        let caches = batchCaches(batch.map(\.caches))

        let logits = loaded.model(tokens, caches: caches)
        let next = batch.indices.map { i in batch[i].sampler(logits[i ..< i + 1, -1, 0...]) }
        eval(next)
        for (s, token) in zip(batch, next) {
            emit(s, token.item(Int.self))
        }
    }

    /// Hands a new token to its sequence and retires the sequence if done.
    private func emit(_ s: Sequence, _ token: Int) {
        if loaded.eosTokens.contains(token) {
            return finish(s, .stop)
        }
        s.generated += 1
        s.last = token
        let (text, stopped) = s.stopper.feed(s.detokenizer.append(token))
        if !text.isEmpty { s.job.continuation.yield(.text(text)) }
        if stopped { return finish(s, .stop, hitStopString: true) }
        if s.generated >= s.job.request.maxTokens { finish(s, .length) }
    }

    private func finish(_ s: Sequence, _ reason: FinishReason, hitStopString: Bool = false) {
        if !hitStopString && reason != .cancelled {
            let rest = s.stopper.finish()
            if !rest.isEmpty { s.job.continuation.yield(.text(rest)) }
        }
        s.job.continuation.yield(.finished(reason, Usage(
            promptTokens: s.job.request.prompt.count, completionTokens: s.generated, cachedTokens: 0)))
        s.job.continuation.finish()
        running.removeAll { $0 === s }
        waiting.removeAll { $0 === s }
    }
}
