import Foundation

/// Text settings of a Qwen3.5 checkpoint (`config.json` -> `text_config`).
public struct Qwen35Config: Codable, Sendable {
    public var hiddenSize: Int
    public var numHiddenLayers: Int
    public var intermediateSize: Int
    public var numAttentionHeads: Int
    public var numKeyValueHeads: Int
    public var headDim: Int
    public var rmsNormEps: Float
    public var vocabSize: Int
    public var tieWordEmbeddings: Bool
    public var layerTypes: [String]
    public var linearNumKeyHeads: Int
    public var linearNumValueHeads: Int
    public var linearKeyHeadDim: Int
    public var linearValueHeadDim: Int
    public var linearConvKernelDim: Int
    public var mtpNumHiddenLayers: Int?
    public var ropeParameters: RopeParameters

    // Mixture of experts (qwen3_5_moe). Absent for dense models.
    public var numExperts: Int?
    public var numExpertsPerTok: Int?
    public var moeIntermediateSize: Int?
    public var sharedExpertIntermediateSize: Int?
    public var normTopkProb: Bool?

    public struct RopeParameters: Codable, Sendable {
        public var ropeTheta: Float
        public var partialRotaryFactor: Float
    }

    /// Number of head dimensions that RoPE rotates. The rest pass through.
    public var ropeDims: Int { Int(Float(headDim) * ropeParameters.partialRotaryFactor) }

    public static func load(from directory: URL) throws -> Qwen35Config {
        struct Root: Codable { var textConfig: Qwen35Config }
        let data = try Data(contentsOf: directory.appending(path: "config.json"))
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(Root.self, from: data).textConfig
    }
}
