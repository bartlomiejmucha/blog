import MLX

/// Speculative decoding with Qwen3.5's MTP head as the drafter.
///
/// Every step:
/// 1. The MTP head has already proposed a draft token `d` for the position
///    after `last`.
/// 2. The main model runs on `[last, d]` in one forward pass. Its first
///    output says what should follow `last`; its second says what follows `d`.
/// 3. If the main model agrees with `d`, both `d` and the token after it
///    are emitted: two tokens for one pass. Otherwise only the main model's
///    own choice is emitted, and the caches forget `d`.
/// 4. The MTP head reads the newly committed positions and drafts again.
///
/// With greedy sampling the output is the same as plain greedy decoding.
/// With temperature > 0 drafts are accepted by rejection sampling, which
/// keeps the output distribution the same as the main model's.
public struct MTPGenerator: Sequence, IteratorProtocol {
    let model: Qwen35Model
    let mtp: MTPHead
    public let caches: [LayerCache]
    let mtpCaches: [KVCache]
    var sampler: Sampler
    let maxTokens: Int

    var last: MLXArray            // [1, 1], the newest committed token
    var draft: MLXArray           // [1, 1]
    var draftLogProbs: MLXArray?  // MTP distribution of the draft, when sampling
    var ready: [Int] = []
    public private(set) var generated = 0
    public private(set) var steps = 0
    public private(set) var accepted = 0

    public init(model: Qwen35Model, prompt: [Int], parameters: SamplingParameters, maxTokens: Int) {
        precondition(model.mtp != nil, "load the model with withMTP: true")
        self.model = model
        self.mtp = model.mtp!
        self.caches = model.makeCaches()
        self.mtpCaches = mtp.makeCaches()
        self.sampler = Sampler(parameters)
        self.maxTokens = maxTokens

        // Prefill the main model on the whole prompt, keeping hidden states.
        let promptArray = MLXArray(prompt.map(Int32.init)).reshaped(1, -1)
        let (logits, hidden) = model.forward(promptArray, caches: caches)
        let first = sampler(logits[0..., -1, 0...]).reshaped(1, 1)

        // Prefill the MTP head. Position i pairs hidden[i] with the token at
        // i+1, so the inputs are the prompt shifted left plus the first token.
        let shifted = concatenated([promptArray[0..., 1...], first.asType(.int32)], axis: 1)
        last = first
        ready = [first.item(Int.self)]
        draft = first
        (draft, draftLogProbs) = propose(tokens: shifted, hidden: hidden)
    }

    /// Runs the MTP head on newly committed (token, hidden) pairs and drafts
    /// the token after the last one.
    mutating func propose(tokens: MLXArray, hidden: MLXArray) -> (MLXArray, MLXArray?) {
        let h = mtp(embeddings: model.embed(tokens), hidden: hidden, caches: mtpCaches)
        let logits = model.logits(h[0..., (-1)..., 0...])[0..., 0, 0...]
        if sampler.parameters.temperature == 0 {
            return (argMax(logits, axis: -1).reshaped(1, 1), nil)
        }
        let logprobs = sampler.logProbabilities(logits)
        return (sampler.sample(fromLogProbs: logprobs).reshaped(1, 1), logprobs)
    }

    mutating func step() {
        steps += 1
        for case let cache as LinearCache in caches { cache.recordSnapshots = true }
        let input = concatenated([last, draft], axis: 1).asType(.int32)
        let (logits, hidden) = model.forward(input, caches: caches)
        for case let cache as LinearCache in caches { cache.recordSnapshots = false }

        // Build the accept decision, the correction and the bonus token as
        // one lazy graph, then read them back with a single GPU sync.
        let (ok, correction) = verify(logits[0..., 0, 0...])
        let bonus = sampler(logits[0..., 1, 0...]).reshaped(1, 1)
        eval(ok, correction, bonus, draft)

        if ok.item(Bool.self) {
            accepted += 1
            // Both positions are committed. The second output is a free extra token.
            ready += [draft.item(Int.self), bonus.item(Int.self)]
            let committed = concatenated([draft, bonus], axis: 1).asType(.int32)
            last = bonus
            (draft, draftLogProbs) = propose(tokens: committed, hidden: hidden)
        } else {
            // Drop the rejected draft from every cache, then commit the fix.
            for cache in caches { cache.trim(1) }
            ready.append(correction.item(Int.self))
            last = correction
            (draft, draftLogProbs) = propose(
                tokens: correction.asType(.int32), hidden: hidden[0..., ..<1, 0...])
        }
    }

    /// Decides whether the main model accepts the draft, and which token to
    /// emit instead if it does not. Both results are lazy arrays.
    mutating func verify(_ targetLogits: MLXArray) -> (ok: MLXArray, correction: MLXArray) {
        guard let q = draftLogProbs else {
            let choice = argMax(targetLogits, axis: -1).reshaped(1, 1)
            return (choice .== draft, choice)
        }
        // Accept with probability min(1, p(d) / q(d)).
        let p = sampler.logProbabilities(targetLogits)
        let ratio = exp(takeAlong(p, draft, axis: -1) - takeAlong(q, draft, axis: -1))
        let ok = sampler.uniform([1, 1]) .< ratio
        // On rejection, sample from the leftover mass max(0, p - q).
        let residual = maximum(exp(p) - exp(q), 0)
        let correction = sampler.sample(fromLogProbs: log(residual)).reshaped(1, 1)
        return (ok, correction)
    }

    public mutating func next() -> Int? {
        guard generated < maxTokens else { return nil }
        if ready.isEmpty { step() }
        generated += 1
        return ready.removeFirst()
    }

    /// Fraction of drafts the main model accepted.
    public var acceptanceRate: Double { steps == 0 ? 0 : Double(accepted) / Double(steps) }
}
