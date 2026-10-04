import Foundation
import MLX
import MLXNN

public enum LoadError: Error {
    case noWeights(URL)
    case unsupported(String)
}

/// Builds a Qwen3 model from a local Hugging Face directory.
public func loadQwen3(from directory: URL) throws -> Qwen3Model {
    let config = try Qwen3Config.load(from: directory)
    let model = Qwen3Model(config)

    // 1. Read every *.safetensors shard into one flat name -> array map.
    let files = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil)
        .filter { $0.pathExtension == "safetensors" }
    guard !files.isEmpty else { throw LoadError.noWeights(directory) }
    var weights = [String: MLXArray]()
    for file in files {
        weights.merge(try loadArrays(url: file)) { _, new in new }
    }

    // Tied models have no separate output projection.
    if config.tieWordEmbeddings { weights["lm_head.weight"] = nil }
    stackExperts(&weights)

    // 2. Swap Linear/Embedding for their quantized versions wherever the
    //    checkpoint ships scales, so the parameter shapes match.
    if let q = config.quantization {
        quantize(model: model) { path, _ in
            weights["\(path).scales"] != nil ? (q.groupSize, q.bits, .affine) : nil
        }
    }

    // 3. Copy the arrays into the module tree. `.all` fails on any missing
    //    or unexpected key, which catches naming mistakes early.
    try model.update(parameters: ModuleParameters.unflattened(weights), verify: [.all])
    eval(model)
    return model
}
