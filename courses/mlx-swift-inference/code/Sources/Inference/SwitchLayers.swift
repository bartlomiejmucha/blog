import MLX
import MLXNN

/// A bank of `E` linear layers stored as one `[E, out, in]` tensor. Each
/// input row is multiplied only by the experts its indices name, so the
/// cost scales with the experts used, not the experts that exist.
public class SwitchLinear: Module, Quantizable {
    @ParameterInfo(key: "weight") var weight: MLXArray

    init(inputDims: Int, outputDims: Int, experts: Int) {
        _weight.wrappedValue = MLXArray.zeros([experts, outputDims, inputDims])
    }

    /// `x`: `[..., 1, in]`, `indices`: `[..., k]`. Returns `[..., k, out]`.
    func callAsFunction(_ x: MLXArray, _ indices: MLXArray, sorted: Bool) -> MLXArray {
        gatherMM(x, weight.swappedAxes(-1, -2), rhsIndices: indices, sortedIndices: sorted)
    }

    public func toQuantized(groupSize: Int, bits: Int, mode: QuantizationMode) -> Module {
        QuantizedSwitchLinear(self, groupSize: groupSize, bits: bits, mode: mode)
    }
}

public final class QuantizedSwitchLinear: SwitchLinear, Quantized {
    @ParameterInfo(key: "scales") var scales: MLXArray
    @ParameterInfo(key: "biases") var biases: MLXArray?
    public let groupSize: Int
    public let bits: Int
    public let mode: QuantizationMode

    init(_ other: SwitchLinear, groupSize: Int, bits: Int, mode: QuantizationMode) {
        self.groupSize = groupSize
        self.bits = bits
        self.mode = mode
        let q = quantized(other.weight, groupSize: groupSize, bits: bits, mode: mode)
        _scales.wrappedValue = q.scales
        _biases.wrappedValue = q.biases
        super.init(inputDims: 0, outputDims: 0, experts: 0)
        self.weight = q.wq
        self.freeze()
    }

    override func callAsFunction(_ x: MLXArray, _ indices: MLXArray, sorted: Bool) -> MLXArray {
        gatherQuantizedMM(
            x, weight, scales: scales, biases: biases, rhsIndices: indices,
            transpose: true, groupSize: groupSize, bits: bits, mode: mode, sortedIndices: sorted)
    }
}

/// SwiGLU MLPs for `E` experts. Each token runs through the `k` experts it
/// was routed to.
final class SwitchGLU: Module {
    @ModuleInfo(key: "gate_proj") var gateProj: SwitchLinear
    @ModuleInfo(key: "up_proj") var upProj: SwitchLinear
    @ModuleInfo(key: "down_proj") var downProj: SwitchLinear

    init(hidden: Int, intermediate: Int, experts: Int) {
        _gateProj.wrappedValue = SwitchLinear(inputDims: hidden, outputDims: intermediate, experts: experts)
        _upProj.wrappedValue = SwitchLinear(inputDims: hidden, outputDims: intermediate, experts: experts)
        _downProj.wrappedValue = SwitchLinear(inputDims: intermediate, outputDims: hidden, experts: experts)
    }

    /// `x`: `[B, L, hidden]`, `indices`: `[B, L, k]`. Returns `[B, L, k, hidden]`.
    func callAsFunction(_ x: MLXArray, _ indices: MLXArray) -> MLXArray {
        let (B, L, k) = (indices.dim(0), indices.dim(1), indices.dim(2))
        var x = expandedDimensions(x, axes: [-2, -3])   // [B, L, 1, 1, hidden]

        // With many tokens (prefill), group rows by expert so each expert's
        // weights are read once, then restore the original order.
        let sort = indices.size >= 64
        var idx = indices
        var inverse: MLXArray?
        if sort {
            let flat = indices.flattened()
            let order = argSort(flat)
            inverse = argSort(order)
            x = x.flattened(start: 0, end: -3)[order.floorDivide(k)]
            idx = flat[order]
        }

        let h = swiglu(gateProj(x, idx, sorted: sort), upProj(x, idx, sorted: sort))
        var y = downProj(h, idx, sorted: sort)

        if let inverse {
            y = y[inverse].reshaped(B, L, k, 1, -1)
        }
        return y.squeezed(axis: -2)
    }
}

/// Mixture-of-experts feed-forward layer.
///
/// A router scores all experts for each token, keeps the top `k`, and mixes
/// their outputs by the renormalized scores. Qwen3.5 adds a shared expert
/// that every token uses, scaled by its own learned gate.
final class SparseMoE: Module, UnaryLayer {
    let topK: Int
    let normalizeTopK: Bool

    @ModuleInfo(key: "gate") var router: Linear
    @ModuleInfo(key: "switch_mlp") var experts: SwitchGLU
    @ModuleInfo(key: "shared_expert") var sharedExpert: Qwen35MLP?
    @ModuleInfo(key: "shared_expert_gate") var sharedExpertGate: Linear?

    init(hidden: Int, intermediate: Int, experts: Int, topK: Int, normalizeTopK: Bool, sharedIntermediate: Int?) {
        self.topK = topK
        self.normalizeTopK = normalizeTopK
        _router.wrappedValue = Linear(hidden, experts, bias: false)
        _experts.wrappedValue = SwitchGLU(hidden: hidden, intermediate: intermediate, experts: experts)
        if let sharedIntermediate {
            _sharedExpert.wrappedValue = Qwen35MLP(hidden: hidden, intermediate: sharedIntermediate)
            _sharedExpertGate.wrappedValue = Linear(hidden, 1, bias: false)
        }
    }

    func callAsFunction(_ x: MLXArray) -> MLXArray {
        let probs = softmax(router(x).asType(.float32), axis: -1)
        let indices = argPartition(probs, kth: -topK, axis: -1)[.ellipsis, (-topK)...]
        var scores = takeAlong(probs, indices, axis: -1)
        if normalizeTopK {
            scores = scores / scores.sum(axis: -1, keepDims: true)
        }

        var y = (experts(x, indices) * scores[.ellipsis, .newAxis]).sum(axis: -2).asType(x.dtype)
        if let sharedExpert, let sharedExpertGate {
            y = y + sigmoid(sharedExpertGate(x)) * sharedExpert(x)
        }
        return y
    }
}

/// Hugging Face checkpoints store each expert separately
/// (`mlp.experts.{e}.gate_proj.weight`). Stack them into the single
/// `[E, out, in]` tensor that `SwitchLinear` expects.
func stackExperts(_ weights: inout [String: MLXArray]) {
    let pattern = /^(.*)\.experts\.(\d+)\.(gate_proj|up_proj|down_proj)\.weight$/
    var groups = [String: [Int: MLXArray]]()
    for (name, array) in weights {
        guard let m = name.wholeMatch(of: pattern) else { continue }
        groups["\(m.1).switch_mlp.\(m.3).weight", default: [:]][Int(m.2)!] = array
        weights[name] = nil
    }
    for (name, experts) in groups {
        weights[name] = stacked((0 ..< experts.count).map { experts[$0]! })
    }
}
