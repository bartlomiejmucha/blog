import MLX
import MLXNN

/// Qwen3.5's multi-token-prediction head.
///
/// The main model's hidden state at position t already encodes "what comes
/// after t". Given that state and the embedding of token t+1, this head runs
/// one extra full-attention decoder layer and predicts token t+2. It shares
/// the main model's embedding table and output projection.
public final class MTPHead: Module {
    @ModuleInfo(key: "pre_fc_norm_embedding") var preNormEmbedding: RMSNorm
    @ModuleInfo(key: "pre_fc_norm_hidden") var preNormHidden: RMSNorm
    @ModuleInfo(key: "fc") var fc: Linear
    @ModuleInfo(key: "layers") var layers: [Qwen35Block]
    @ModuleInfo(key: "norm") var norm: RMSNorm

    init(_ c: Qwen35Config) {
        _preNormEmbedding.wrappedValue = RMSNorm(dimensions: c.hiddenSize, eps: c.rmsNormEps)
        _preNormHidden.wrappedValue = RMSNorm(dimensions: c.hiddenSize, eps: c.rmsNormEps)
        _fc.wrappedValue = Linear(2 * c.hiddenSize, c.hiddenSize, bias: false)
        _layers.wrappedValue = (0 ..< (c.mtpNumHiddenLayers ?? 1)).map { _ in Qwen35Block(c, linear: false) }
        _norm.wrappedValue = RMSNorm(dimensions: c.hiddenSize, eps: c.rmsNormEps)
    }

    /// `embeddings` and `hidden` are `[B, L, hidden]`: the embedding of token
    /// t+1 paired with the main model's final hidden state at t. Returns the
    /// head's hidden state, which the shared output projection turns into
    /// logits for token t+2.
    public func callAsFunction(embeddings: MLXArray, hidden: MLXArray, caches: [KVCache]) -> MLXArray {
        var h = fc(concatenated([preNormEmbedding(embeddings), preNormHidden(hidden)], axis: -1))
        for (layer, cache) in zip(layers, caches) {
            h = layer(h, cache: cache)
        }
        return norm(h)
    }

    public func makeCaches() -> [KVCache] {
        layers.map { _ in KVCache() }
    }
}
