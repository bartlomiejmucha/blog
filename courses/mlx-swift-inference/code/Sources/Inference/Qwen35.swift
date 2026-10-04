import MLX
import MLXNN

/// Full attention with an output gate: `q_proj` produces queries and a
/// per-channel gate, and the attention output is multiplied by
/// `sigmoid(gate)` before `o_proj`. RoPE rotates only the first `ropeDims`
/// dimensions of each head.
final class GatedAttention: Module {
    let heads: Int
    let kvHeads: Int
    let headDim: Int
    let ropeDims: Int
    let ropeTheta: Float
    let scale: Float

    @ModuleInfo(key: "q_proj") var qProj: Linear
    @ModuleInfo(key: "k_proj") var kProj: Linear
    @ModuleInfo(key: "v_proj") var vProj: Linear
    @ModuleInfo(key: "o_proj") var oProj: Linear
    @ModuleInfo(key: "q_norm") var qNorm: RMSNorm
    @ModuleInfo(key: "k_norm") var kNorm: RMSNorm

    init(_ c: Qwen35Config) {
        heads = c.numAttentionHeads
        kvHeads = c.numKeyValueHeads
        headDim = c.headDim
        ropeDims = c.ropeDims
        ropeTheta = c.ropeParameters.ropeTheta
        scale = 1 / Float(headDim).squareRoot()
        _qProj.wrappedValue = Linear(c.hiddenSize, heads * headDim * 2, bias: false)
        _kProj.wrappedValue = Linear(c.hiddenSize, kvHeads * headDim, bias: false)
        _vProj.wrappedValue = Linear(c.hiddenSize, kvHeads * headDim, bias: false)
        _oProj.wrappedValue = Linear(heads * headDim, c.hiddenSize, bias: false)
        _qNorm.wrappedValue = RMSNorm(dimensions: headDim, eps: c.rmsNormEps)
        _kNorm.wrappedValue = RMSNorm(dimensions: headDim, eps: c.rmsNormEps)
    }

    func callAsFunction(_ x: MLXArray, cache: LayerCache?) -> MLXArray {
        let (B, L) = (x.dim(0), x.dim(1))

        let qg = qProj(x).reshaped(B, L, heads, 2 * headDim)
        let parts = split(qg, parts: 2, axis: -1)
        let gate = parts[1].reshaped(B, L, heads * headDim)

        let q = qNorm(parts[0]).transposed(0, 2, 1, 3)
        let k = kNorm(kProj(x).reshaped(B, L, kvHeads, headDim)).transposed(0, 2, 1, 3)
        let v = vProj(x).reshaped(B, L, kvHeads, headDim).transposed(0, 2, 1, 3)

        let out = attend(q: q, k: k, v: v, cache: cache, scale: scale) { [ropeDims, ropeTheta] x, offset in
            MLXFast.RoPE(x, dimensions: ropeDims, traditional: false, base: ropeTheta, scale: 1, offset: offset)
        }
        .transposed(0, 2, 1, 3).reshaped(B, L, heads * headDim)
        return oProj(out * sigmoid(gate))
    }
}

/// RMSNorm whose output is multiplied by `silu(gate)`, computed in float32.
final class GatedRMSNorm: Module {
    let eps: Float
    var weight: MLXArray

    init(dimensions: Int, eps: Float) {
        self.eps = eps
        weight = MLXArray.ones([dimensions])
    }

    func callAsFunction(_ x: MLXArray, gate: MLXArray) -> MLXArray {
        let normed = MLXFast.rmsNorm(x, weight: weight, eps: eps)
        return (silu(gate.asType(.float32)) * normed.asType(.float32)).asType(x.dtype)
    }
}

/// Gated DeltaNet: linear attention whose state is a fixed-size matrix per
/// head instead of a growing list of keys and values.
final class GatedDeltaNet: Module {
    let numKHeads: Int
    let numVHeads: Int
    let headKDim: Int
    let headVDim: Int
    let keyDim: Int
    let valueDim: Int
    let convDim: Int
    let convKernel: Int

    @ModuleInfo(key: "in_proj_qkv") var inProjQKV: Linear
    @ModuleInfo(key: "in_proj_z") var inProjZ: Linear
    @ModuleInfo(key: "in_proj_b") var inProjB: Linear
    @ModuleInfo(key: "in_proj_a") var inProjA: Linear
    @ModuleInfo(key: "conv1d") var conv1d: Conv1d
    @ModuleInfo(key: "norm") var norm: GatedRMSNorm
    @ModuleInfo(key: "out_proj") var outProj: Linear
    @ParameterInfo(key: "A_log") var aLog: MLXArray
    @ParameterInfo(key: "dt_bias") var dtBias: MLXArray

    init(_ c: Qwen35Config) {
        numKHeads = c.linearNumKeyHeads
        numVHeads = c.linearNumValueHeads
        headKDim = c.linearKeyHeadDim
        headVDim = c.linearValueHeadDim
        keyDim = numKHeads * headKDim
        valueDim = numVHeads * headVDim
        convDim = 2 * keyDim + valueDim
        convKernel = c.linearConvKernelDim

        _inProjQKV.wrappedValue = Linear(c.hiddenSize, convDim, bias: false)
        _inProjZ.wrappedValue = Linear(c.hiddenSize, valueDim, bias: false)
        _inProjB.wrappedValue = Linear(c.hiddenSize, numVHeads, bias: false)
        _inProjA.wrappedValue = Linear(c.hiddenSize, numVHeads, bias: false)
        _conv1d.wrappedValue = Conv1d(
            inputChannels: convDim, outputChannels: convDim, kernelSize: convKernel,
            groups: convDim, bias: false)
        _norm.wrappedValue = GatedRMSNorm(dimensions: headVDim, eps: c.rmsNormEps)
        _outProj.wrappedValue = Linear(valueDim, c.hiddenSize, bias: false)
        _aLog.wrappedValue = MLXArray.zeros([numVHeads])
        _dtBias.wrappedValue = MLXArray.ones([numVHeads])
    }

    func callAsFunction(_ x: MLXArray, cache: LayerCache?) -> MLXArray {
        let (B, S) = (x.dim(0), x.dim(1))
        let single = cache as? LinearCache
        let batch = cache as? BatchLinearCache

        let qkv = inProjQKV(x)
        let z = inProjZ(x).reshaped(B, S, numVHeads, headVDim)
        let b = inProjB(x)
        let a = inProjA(x)

        // Short causal convolution over the last `convKernel` positions. The
        // cache supplies the inputs that came before this call.
        let convState = batch?.conv ?? single?.conv ?? MLXArray.zeros([B, convKernel - 1, convDim], dtype: x.dtype)
        let convInput = concatenated([convState, qkv], axis: 1)
        let convOut = silu(conv1d(convInput))

        let pieces = split(convOut, indices: [keyDim, 2 * keyDim], axis: -1)
        var q = pieces[0].reshaped(B, S, numKHeads, headKDim)
        var k = pieces[1].reshaped(B, S, numKHeads, headKDim)
        let v = pieces[2].reshaped(B, S, numVHeads, headVDim)

        // L2-normalize q and k, and fold the 1/sqrt(Dk) readout scale into q.
        let invScale = 1 / Float(headKDim).squareRoot()
        let ones = MLXArray.ones([headKDim], dtype: q.dtype)
        q = (invScale * invScale) * MLXFast.rmsNorm(q, weight: ones, eps: 1e-6 * invScale * invScale)
        k = invScale * MLXFast.rmsNorm(k, weight: ones, eps: 1e-6 * invScale * invScale)
        if numVHeads > numKHeads {
            q = repeated(q, count: numVHeads / numKHeads, axis: 2)
            k = repeated(k, count: numVHeads / numKHeads, axis: 2)
        }

        // Per-token, per-head decay g in (0, 1) and write strength beta in (0, 1).
        let g = exp(-exp(aLog.asType(.float32)) * softplus(a + dtBias))
        let beta = sigmoid(b)

        let state = batch?.recurrent ?? single?.recurrent ?? MLXArray.zeros([B, numVHeads, headVDim, headKDim], dtype: .float32)
        var y: MLXArray
        var newState: MLXArray
        var snapshots = [(MLXArray, MLXArray)]()
        let record = single?.recordSnapshots ?? false
        if gatedDeltaUseKernel {
            let history: MLXArray?
            (y, newState, history) = gatedDeltaMetal(
                q: q, k: k, v: v, g: g, beta: beta, state: state, saveHistory: record)
            if let history {
                // After token t the conv window is convInput[t+1 ..< t+convKernel].
                snapshots = (0 ..< S).map { t in
                    (convInput[0..., (t + 1) ..< (t + convKernel), 0...], history[t])
                }
            }
        } else {
            let states: [MLXArray]
            (y, newState, states) = gatedDeltaOps(q: q, k: k, v: v, g: g, beta: beta, state: state)
            if record {
                snapshots = states.enumerated().map { t, s in
                    (convInput[0..., (t + 1) ..< (t + convKernel), 0...], s)
                }
            }
        }

        let newConv = convInput[0..., (-(convKernel - 1))..., 0...]
        single?.update(conv: newConv, recurrent: newState, count: S, snapshots: snapshots)
        batch?.update(conv: newConv, recurrent: newState, count: S)

        y = norm(y, gate: z)
        return outProj(y.reshaped(B, S, valueDim))
    }
}

final class Qwen35MLP: Module, UnaryLayer {
    @ModuleInfo(key: "gate_proj") var gateProj: Linear
    @ModuleInfo(key: "up_proj") var upProj: Linear
    @ModuleInfo(key: "down_proj") var downProj: Linear

    init(hidden: Int, intermediate: Int) {
        _gateProj.wrappedValue = Linear(hidden, intermediate, bias: false)
        _upProj.wrappedValue = Linear(hidden, intermediate, bias: false)
        _downProj.wrappedValue = Linear(intermediate, hidden, bias: false)
    }

    func callAsFunction(_ x: MLXArray) -> MLXArray {
        downProj(swiglu(gateProj(x), upProj(x)))
    }
}

final class Qwen35Block: Module {
    @ModuleInfo(key: "linear_attn") var linearAttention: GatedDeltaNet?
    @ModuleInfo(key: "self_attn") var attention: GatedAttention?
    @ModuleInfo(key: "mlp") var mlp: UnaryLayer
    @ModuleInfo(key: "input_layernorm") var inputNorm: RMSNorm
    @ModuleInfo(key: "post_attention_layernorm") var postAttentionNorm: RMSNorm

    init(_ c: Qwen35Config, linear: Bool) {
        if linear {
            _linearAttention.wrappedValue = GatedDeltaNet(c)
        } else {
            _attention.wrappedValue = GatedAttention(c)
        }
        if let experts = c.numExperts, experts > 0 {
            _mlp.wrappedValue = SparseMoE(
                hidden: c.hiddenSize, intermediate: c.moeIntermediateSize!, experts: experts,
                topK: c.numExpertsPerTok!, normalizeTopK: c.normTopkProb ?? true,
                sharedIntermediate: c.sharedExpertIntermediateSize)
        } else {
            _mlp.wrappedValue = Qwen35MLP(hidden: c.hiddenSize, intermediate: c.intermediateSize)
        }
        _inputNorm.wrappedValue = RMSNorm(dimensions: c.hiddenSize, eps: c.rmsNormEps)
        _postAttentionNorm.wrappedValue = RMSNorm(dimensions: c.hiddenSize, eps: c.rmsNormEps)
    }

    func callAsFunction(_ x: MLXArray, cache: LayerCache?) -> MLXArray {
        let mixed: MLXArray
        if let linearAttention {
            mixed = linearAttention(inputNorm(x), cache: cache)
        } else {
            mixed = attention!(inputNorm(x), cache: cache)
        }
        let h = x + mixed
        return h + mlp(postAttentionNorm(h))
    }
}

final class Qwen35Backbone: Module {
    @ModuleInfo(key: "embed_tokens") var embedTokens: Embedding
    @ModuleInfo(key: "layers") var layers: [Qwen35Block]
    @ModuleInfo(key: "norm") var norm: RMSNorm

    init(_ c: Qwen35Config) {
        _embedTokens.wrappedValue = Embedding(embeddingCount: c.vocabSize, dimensions: c.hiddenSize)
        _layers.wrappedValue = c.layerTypes.map { Qwen35Block(c, linear: $0 == "linear_attention") }
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

/// Qwen3.5 text decoder: three Gated DeltaNet layers for every full
/// attention layer, plus an optional multi-token-prediction head.
public final class Qwen35Model: Module, LanguageModel {
    public let config: Qwen35Config
    @ModuleInfo(key: "model") var model: Qwen35Backbone
    @ModuleInfo(key: "lm_head") var lmHead: Linear?
    @ModuleInfo(key: "mtp") public var mtp: MTPHead?

    public init(_ config: Qwen35Config, withMTP: Bool) {
        self.config = config
        _model.wrappedValue = Qwen35Backbone(config)
        if !config.tieWordEmbeddings {
            _lmHead.wrappedValue = Linear(config.hiddenSize, config.vocabSize, bias: false)
        }
        if withMTP {
            _mtp.wrappedValue = MTPHead(config)
        }
    }

    /// Logits for every position, `[B, L, vocab]`.
    public func callAsFunction(_ tokens: MLXArray, caches: [LayerCache]?) -> MLXArray {
        logits(model(tokens, caches: caches))
    }

    /// Final hidden states `[B, L, hidden]` together with their logits. The
    /// MTP head needs the hidden states.
    public func forward(_ tokens: MLXArray, caches: [LayerCache]?) -> (logits: MLXArray, hidden: MLXArray) {
        let h = model(tokens, caches: caches)
        return (logits(h), h)
    }

    public func logits(_ hidden: MLXArray) -> MLXArray {
        lmHead?(hidden) ?? model.embedTokens.asLinear(hidden)
    }

    public func embed(_ tokens: MLXArray) -> MLXArray {
        model.embedTokens(tokens)
    }

    public func makeCaches() -> [LayerCache] {
        model.layers.map { $0.linearAttention != nil ? LinearCache() as LayerCache : KVCache() }
    }
}
