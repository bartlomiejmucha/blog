import MLX

/// What the generation loop needs from a model.
public protocol LanguageModel: AnyObject {
    /// Token ids `[B, L]` to logits `[B, L, vocab]`, updating `caches`.
    func callAsFunction(_ tokens: MLXArray, caches: [LayerCache]?) -> MLXArray
    /// One fresh cache per layer.
    func makeCaches() -> [LayerCache]
}
