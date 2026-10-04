import Foundation
import MLX
import Tokenizers

/// A model plus everything needed to talk to it in text.
public final class LoadedModel {
    public let name: String
    public let model: any LanguageModel
    public let tokenizer: any Tokenizer
    public let eosTokens: Set<Int>
    /// `<|im_start|>`: where each chat turn begins.
    public var turnStartToken: Int? { tokenizer.convertTokenToId("<|im_start|>") }

    public init(name: String, model: any LanguageModel, tokenizer: any Tokenizer, eosTokens: Set<Int>) {
        self.name = name
        self.model = model
        self.tokenizer = tokenizer
        self.eosTokens = eosTokens
    }

    /// Picks the architecture from `model_type` in `config.json`.
    public static func load(directory: URL, name: String? = nil, quantizeBits: Int? = 4) async throws -> LoadedModel {
        struct Header: Decodable { var modelType: String }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let header = try decoder.decode(Header.self, from: Data(contentsOf: directory.appending(path: "config.json")))

        let model: any LanguageModel
        switch header.modelType {
        case "qwen3", "qwen3_moe":
            model = try loadQwen3(from: directory)
        case "qwen3_5", "qwen3_5_moe":
            model = try loadQwen35(from: directory, withMTP: true, quantizeBits: quantizeBits)
        default:
            throw LoadError.unsupported(header.modelType)
        }

        let tokenizer = try await AutoTokenizer.from(modelFolder: directory)
        // Chat models end a turn with <|im_end|>; base models with <|endoftext|>.
        let eos = Set([tokenizer.eosTokenId,
                       tokenizer.convertTokenToId("<|im_end|>"),
                       tokenizer.convertTokenToId("<|endoftext|>")].compactMap { $0 })
        return LoadedModel(
            name: name ?? directory.lastPathComponent, model: model, tokenizer: tokenizer, eosTokens: eos)
    }

    /// Formats a conversation, and the tools the model may call, with the
    /// model's chat template.
    public func prompt(
        messages: [[String: any Sendable]], tools: [[String: any Sendable]]? = nil, enableThinking: Bool = false
    ) throws -> [Int] {
        try tokenizer.applyChatTemplate(
            messages: messages, tools: tools, additionalContext: ["enable_thinking": enableThinking])
    }
}

/// Renders chat prompts from request handlers on any thread. The tokenizer
/// is not documented as thread-safe, so calls go through a lock.
public final class PromptFormatter: @unchecked Sendable {
    private let loaded: LoadedModel
    private let lock = NSLock()

    public init(_ loaded: LoadedModel) {
        self.loaded = loaded
    }

    public func render(
        messages: [[String: any Sendable]], tools: [[String: any Sendable]]?, enableThinking: Bool
    ) throws -> [Int] {
        try lock.withLock { try loaded.prompt(messages: messages, tools: tools, enableThinking: enableThinking) }
    }
}
