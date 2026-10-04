import Foundation

/// The subset of a Hugging Face `config.json` that a Qwen3 dense model needs.
public struct Qwen3Config: Codable, Sendable {
    public var hiddenSize: Int
    public var numHiddenLayers: Int
    public var intermediateSize: Int
    public var numAttentionHeads: Int
    public var numKeyValueHeads: Int
    public var headDim: Int
    public var rmsNormEps: Float
    public var ropeTheta: Float
    public var vocabSize: Int
    public var tieWordEmbeddings: Bool
    public var quantization: Quantization?

    // Mixture of experts (qwen3_moe). Absent for dense models.
    public var numExperts: Int?
    public var numExpertsPerTok: Int?
    public var moeIntermediateSize: Int?
    public var decoderSparseStep: Int?
    public var mlpOnlyLayers: [Int]?
    public var normTopkProb: Bool?

    func isMoELayer(_ i: Int) -> Bool {
        guard let n = numExperts, n > 0 else { return false }
        return !(mlpOnlyLayers ?? []).contains(i) && (i + 1) % (decoderSparseStep ?? 1) == 0
    }

    public struct Quantization: Codable, Sendable {
        public var groupSize: Int
        public var bits: Int
    }

    public static func load(from directory: URL) throws -> Qwen3Config {
        let data = try Data(contentsOf: directory.appending(path: "config.json"))
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(Qwen3Config.self, from: data)
    }
}
