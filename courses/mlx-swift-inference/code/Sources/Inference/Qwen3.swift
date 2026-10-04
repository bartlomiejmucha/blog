import MLX
import MLXNN

final class Attention: Module {
    let heads: Int
    let kvHeads: Int
    let headDim: Int
    let scale: Float
    let ropeTheta: Float

    @ModuleInfo(key: "q_proj") var qProj: Linear
    @ModuleInfo(key: "k_proj") var kProj: Linear
    @ModuleInfo(key: "v_proj") var vProj: Linear
    @ModuleInfo(key: "o_proj") var oProj: Linear
    @ModuleInfo(key: "q_norm") var qNorm: RMSNorm
    @ModuleInfo(key: "k_norm") var kNorm: RMSNorm

    init(_ c: Qwen3Config) {
        heads = c.numAttentionHeads
        kvHeads = c.numKeyValueHeads
        headDim = c.headDim
        scale = 1 / Float(c.headDim).squareRoot()
        ropeTheta = c.ropeTheta
        _qProj.wrappedValue = Linear(c.hiddenSize, heads * headDim, bias: false)
        _kProj.wrappedValue = Linear(c.hiddenSize, kvHeads * headDim, bias: false)
        _vProj.wrappedValue = Linear(c.hiddenSize, kvHeads * headDim, bias: false)
        _oProj.wrappedValue = Linear(heads * headDim, c.hiddenSize, bias: false)
        _qNorm.wrappedValue = RMSNorm(dimensions: headDim, eps: c.rmsNormEps)
        _kNorm.wrappedValue = RMSNorm(dimensions: headDim, eps: c.rmsNormEps)
    }

    func callAsFunction(_ x: MLXArray, cache: LayerCache?) -> MLXArray {
        let (B, L) = (x.dim(0), x.dim(1))

        // [B, L, hidden] -> [B, heads, L, headDim]
        let q = qNorm(qProj(x).reshaped(B, L, heads, headDim)).transposed(0, 2, 1, 3)
        let k = kNorm(kProj(x).reshaped(B, L, kvHeads, headDim)).transposed(0, 2, 1, 3)
        let v = vProj(x).reshaped(B, L, kvHeads, headDim).transposed(0, 2, 1, 3)

        let out = attend(q: q, k: k, v: v, cache: cache, scale: scale) { [headDim, ropeTheta] x, offset in
            MLXFast.RoPE(x, dimensions: headDim, traditional: false, base: ropeTheta, scale: 1, offset: offset)
        }
        return oProj(out.transposed(0, 2, 1, 3).reshaped(B, L, heads * headDim))
    }
}

/// `silu(gate) * x` fused into one kernel, so the product is rounded to
/// bf16 once instead of twice. This matches the Python reference exactly.
let swiglu = compile(shapeless: true) { (gate: MLXArray, x: MLXArray) in
    silu(gate) * x
}

final class MLP: Module, UnaryLayer {
    @ModuleInfo(key: "gate_proj") var gateProj: Linear
    @ModuleInfo(key: "up_proj") var upProj: Linear
    @ModuleInfo(key: "down_proj") var downProj: Linear

    init(_ c: Qwen3Config) {
        _gateProj.wrappedValue = Linear(c.hiddenSize, c.intermediateSize, bias: false)
        _upProj.wrappedValue = Linear(c.hiddenSize, c.intermediateSize, bias: false)
        _downProj.wrappedValue = Linear(c.intermediateSize, c.hiddenSize, bias: false)
    }

    func callAsFunction(_ x: MLXArray) -> MLXArray {
        downProj(swiglu(gateProj(x), upProj(x)))
    }
}

final class TransformerBlock: Module {
    @ModuleInfo(key: "self_attn") var attention: Attention
    @ModuleInfo(key: "mlp") var mlp: UnaryLayer
    @ModuleInfo(key: "input_layernorm") var inputNorm: RMSNorm
    @ModuleInfo(key: "post_attention_layernorm") var postAttentionNorm: RMSNorm

    init(_ c: Qwen3Config, index: Int) {
        _attention.wrappedValue = Attention(c)
        if c.isMoELayer(index) {
            _mlp.wrappedValue = SparseMoE(
                hidden: c.hiddenSize, intermediate: c.moeIntermediateSize!, experts: c.numExperts!,
                topK: c.numExpertsPerTok!, normalizeTopK: c.normTopkProb ?? true, sharedIntermediate: nil)
        } else {
            _mlp.wrappedValue = MLP(c)
        }
        _inputNorm.wrappedValue = RMSNorm(dimensions: c.hiddenSize, eps: c.rmsNormEps)
        _postAttentionNorm.wrappedValue = RMSNorm(dimensions: c.hiddenSize, eps: c.rmsNormEps)
    }

    func callAsFunction(_ x: MLXArray, cache: LayerCache?) -> MLXArray {
        let h = x + attention(inputNorm(x), cache: cache)
        return h + mlp(postAttentionNorm(h))
    }
}

final class Qwen3Backbone: Module {
    @ModuleInfo(key: "embed_tokens") var embedTokens: Embedding
    @ModuleInfo(key: "layers") var layers: [TransformerBlock]
    @ModuleInfo(key: "norm") var norm: RMSNorm

    init(_ c: Qwen3Config) {
        _embedTokens.wrappedValue = Embedding(embeddingCount: c.vocabSize, dimensions: c.hiddenSize)
        _layers.wrappedValue = (0 ..< c.numHiddenLayers).map { TransformerBlock(c, index: $0) }
        _norm.wrappedValue = RMSNorm(dimensions: c.hiddenSize, eps: c.rmsNormEps)
    }

    func callAsFunction(_ tokens: MLXArray, caches: [LayerCache]?) -> MLXArray {
        var h = embedTokens(tokens)
        for (i, layer) in layers.enumerated() {
            h = layer(h, cache: caches?[i])
        }
        return norm(h)
    }
}

/// Qwen3 decoder, dense or mixture-of-experts. Maps token ids `[B, L]` to logits `[B, L, vocab]`.
public final class Qwen3Model: Module, LanguageModel {
    public let config: Qwen3Config
    @ModuleInfo(key: "model") var model: Qwen3Backbone
    @ModuleInfo(key: "lm_head") var lmHead: Linear?

    public init(_ config: Qwen3Config) {
        self.config = config
        _model.wrappedValue = Qwen3Backbone(config)
        if !config.tieWordEmbeddings {
            _lmHead.wrappedValue = Linear(config.hiddenSize, config.vocabSize, bias: false)
        }
    }

    public func callAsFunction(_ tokens: MLXArray, caches: [LayerCache]?) -> MLXArray {
        let h = model(tokens, caches: caches)
        // Tied models reuse the embedding matrix as the output projection.
        return lmHead?(h) ?? model.embedTokens.asLinear(h)
    }

    public func makeCaches() -> [LayerCache] {
        (0 ..< config.numHiddenLayers).map { _ in KVCache() }
    }
}
