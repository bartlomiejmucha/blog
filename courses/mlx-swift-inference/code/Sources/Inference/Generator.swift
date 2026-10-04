import MLX

/// Produces tokens one at a time for a single sequence.
///
/// The prompt is processed in chunks (prefill), then the loop feeds each
/// sampled token back in (decode). The next step is queued on the GPU before
/// the current token is handed to the caller, so the CPU work between steps
/// overlaps with GPU work.
public struct TokenGenerator: Sequence, IteratorProtocol {
    let model: any LanguageModel
    public let caches: [LayerCache]
    var sampler: Sampler
    var pending: MLXArray
    let maxTokens: Int
    public private(set) var generated = 0
    /// Every token that has been run through the model, in order. The
    /// caches hold exactly these positions.
    public private(set) var fed: [Int] = []
    /// Copies of the caches taken when prefill reached `checkpoint`.
    public private(set) var checkpointCaches: [LayerCache]?

    public init(
        model: any LanguageModel, prompt: [Int], parameters: SamplingParameters,
        maxTokens: Int, caches: [LayerCache]? = nil, prefillStep: Int = 512,
        checkpoint: Int? = nil
    ) {
        self.model = model
        self.caches = caches ?? model.makeCaches()
        self.sampler = Sampler(parameters)
        self.maxTokens = maxTokens

        // Prefill all but the last prompt token in chunks. Only the cache
        // matters here, the logits are thrown away.
        var rest = prompt[...]
        fed = prompt
        while rest.count > 1 {
            var size = Swift.min(prefillStep, rest.count - 1)
            // End a chunk exactly at the checkpoint so the caches can be copied there.
            if let checkpoint, rest.startIndex < checkpoint {
                size = Swift.min(size, checkpoint - rest.startIndex)
            }
            let chunk = rest.prefix(size)
            _ = model(MLXArray(chunk.map(Int32.init)).reshaped(1, -1), caches: self.caches)
            eval(self.caches.flatMap(\.state))
            rest = rest.dropFirst(chunk.count)
            if rest.startIndex == checkpoint {
                checkpointCaches = self.caches.map { $0.copy() }
            }
        }
        pending = MLXArray(rest.map(Int32.init)).reshaped(1, -1)
        pending = step(pending)
        asyncEval(pending)
    }

    mutating func step(_ input: MLXArray) -> MLXArray {
        let logits = model(input, caches: caches)
        return sampler(logits[0..., -1, 0...])
    }

    public mutating func next() -> Int? {
        guard generated < maxTokens else { return nil }
        let current = pending
        if generated + 1 < maxTokens {
            // Queue step n+1 before reading token n off the GPU.
            pending = step(current.reshaped(1, 1))
            asyncEval(pending)
        }
        generated += 1
        let token = current.item(Int.self)
        if generated < maxTokens { fed.append(token) }
        return token
    }
}
