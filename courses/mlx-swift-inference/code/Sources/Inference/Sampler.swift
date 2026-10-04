import MLX

public struct SamplingParameters: Sendable {
    public var temperature: Float = 0
    public var topK: Int = 0       // 0 disables
    public var topP: Float = 1     // 1 disables
    public var minP: Float = 0     // 0 disables
    public var seed: UInt64?

    public init(temperature: Float = 0, topK: Int = 0, topP: Float = 1, minP: Float = 0, seed: UInt64? = nil) {
        self.temperature = temperature
        self.topK = topK
        self.topP = topP
        self.minP = minP
        self.seed = seed
    }
}

/// Turns the logits for the last position, `[B, vocab]`, into token ids `[B]`.
public struct Sampler {
    public let parameters: SamplingParameters
    var key: MLXArray?

    public init(_ parameters: SamplingParameters) {
        self.parameters = parameters
        key = parameters.seed.map { MLXRandom.key($0) }
    }

    public mutating func callAsFunction(_ logits: MLXArray) -> MLXArray {
        if parameters.temperature == 0 {
            return argMax(logits, axis: -1)
        }
        return sample(fromLogProbs: logProbabilities(logits))
    }

    /// Draws one token from `logprobs` (`[B, vocab]`), using the seeded key
    /// if there is one.
    public mutating func sample(fromLogProbs logprobs: MLXArray) -> MLXArray {
        if let current = key {
            let parts = MLXRandom.split(key: current)
            key = parts.0
            return MLXRandom.categorical(logprobs, key: parts.1)
        }
        return MLXRandom.categorical(logprobs)
    }

    /// Uniform random numbers, from the same seeded stream as `sample`.
    public mutating func uniform(_ shape: [Int]) -> MLXArray {
        if let current = key {
            let parts = MLXRandom.split(key: current)
            key = parts.0
            return MLXRandom.uniform(0 ..< 1, shape, key: parts.1)
        }
        return MLXRandom.uniform(0 ..< 1, shape)
    }

    /// The distribution the sampler draws from, as log-probabilities: the
    /// logits after temperature, top-k, min-p and top-p. Requires
    /// temperature > 0.
    public func logProbabilities(_ logits: MLXArray) -> MLXArray {
        let p = parameters
        let scaled = logits.asType(.float32) / p.temperature
        var logprobs = scaled - scaled.logSumExp(axis: -1, keepDims: true)
        let masked = MLXArray(-Float.infinity)

        if p.topK > 0 && p.topK < logprobs.dim(-1) {
            // The k-th largest value is the cutoff. argPartition puts it at
            // index vocab-k without fully sorting.
            let kth = takeAlong(logprobs, argPartition(logprobs, kth: -p.topK, axis: -1)[.ellipsis, (-p.topK)...(-p.topK)], axis: -1)
            logprobs = which(logprobs .< kth, masked, logprobs)
        }

        if p.minP > 0 {
            // Keep tokens whose probability is at least minP times the top one.
            let threshold = logprobs.max(axis: -1, keepDims: true) + log(MLXArray(p.minP))
            logprobs = which(logprobs .< threshold, masked, logprobs)
        }

        if p.topP < 1 {
            // Sort descending, keep the smallest prefix whose mass reaches topP.
            let order = argSort(-logprobs, axis: -1)
            let sorted = takeAlong(logprobs, order, axis: -1)
            let cumulative = cumsum(exp(sorted), axis: -1)
            // A token survives if the mass *before* it is still below topP.
            let keep = (cumulative - exp(sorted)) .< p.topP
            let filtered = which(keep, sorted, masked)
            logprobs = putAlong(logprobs, order, values: filtered, axis: -1)
        }

        // Renormalize what survived.
        return logprobs - logprobs.logSumExp(axis: -1, keepDims: true)
    }
}
