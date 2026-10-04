import Foundation
import MLX
import MLXNN

/// Loads the text model (and MTP head) from an original Hugging Face
/// Qwen3.5 checkpoint, optionally quantizing it on the fly.
public func loadQwen35(
    from directory: URL, withMTP: Bool = true, quantizeBits: Int? = 4, groupSize: Int = 64
) throws -> Qwen35Model {
    let config = try Qwen35Config.load(from: directory)
    let model = Qwen35Model(config, withMTP: withMTP)

    let files = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        .filter { $0.pathExtension == "safetensors" }
    guard !files.isEmpty else { throw LoadError.noWeights(directory) }

    var weights = [String: MLXArray]()
    for file in files {
        for (name, array) in try loadArrays(url: file) {
            if let renamed = sanitize(name, withMTP: withMTP) {
                weights[renamed] = array
            }
        }
    }

    if config.tieWordEmbeddings { weights["lm_head.weight"] = nil }
    stackExperts(&weights)

    for (name, array) in weights {
        // PyTorch stores depthwise conv weights as [out, 1, kernel];
        // MLX wants [out, kernel, 1].
        if name.hasSuffix("conv1d.weight") && array.dim(-1) != 1 {
            weights[name] = array.swappedAxes(1, 2)
        }
        // Qwen3.5 RMSNorms scale by (1 + w) and store only w. MLX's RMSNorm
        // scales by w, so add the 1 back once at load time.
        if isShiftedNorm(name) {
            weights[name] = array + 1
        }
    }

    try model.update(parameters: ModuleParameters.unflattened(weights), verify: [.all])

    if let bits = quantizeBits {
        quantize(model: model) { path, module in
            // Quantize every matrix whose input width splits into whole
            // groups. Anything else (norms, conv, A_log, tiny test models)
            // stays in bf16.
            let inputs: Int
            switch module {
            case let m as Linear: inputs = m.weight.dim(-1)
            case let m as SwitchLinear: inputs = m.weight.dim(-1)
            case let m as Embedding: inputs = m.weight.dim(-1)
            default: return nil
            }
            return inputs % groupSize == 0 ? (groupSize, bits, .affine) : nil
        }
    }
    eval(model)
    return model
}

private func sanitize(_ name: String, withMTP: Bool) -> String? {
    if name.hasPrefix("model.visual") { return nil }
    if name.hasPrefix("mtp.") { return withMTP ? name : nil }
    if name.hasPrefix("model.language_model.") {
        return "model." + name.dropFirst("model.language_model.".count)
    }
    if name.hasPrefix("lm_head.") { return name }
    return nil
}

private func isShiftedNorm(_ name: String) -> Bool {
    guard !name.contains("linear_attn.norm") else { return false }
    return ["input_layernorm.weight", "post_attention_layernorm.weight", "q_norm.weight",
            "k_norm.weight", "model.norm.weight", "mtp.norm.weight",
            "pre_fc_norm_embedding.weight", "pre_fc_norm_hidden.weight"]
        .contains { name.hasSuffix($0) }
}
