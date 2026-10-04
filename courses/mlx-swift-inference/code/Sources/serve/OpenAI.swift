import Foundation

// The subset of the OpenAI Chat Completions wire format this server speaks.

struct ChatMessage: Encodable {
    var role: String
    var content: String?
    var toolCalls: [ToolCallBody]?
}

struct ToolCallBody: Encodable {
    struct Function: Encodable {
        var name: String
        var arguments: String
    }
    var index: Int?
    var id: String
    var type = "function"
    var function: Function
}

/// Scalar request fields. `messages` and `tools` are read separately as
/// untyped JSON, because they go straight into the chat template.
struct ChatRequest: Decodable {
    var model: String?
    var stream: Bool?
    var temperature: Float?
    var topP: Float?
    var topK: Int?
    var minP: Float?
    var seed: UInt64?
    var maxTokens: Int?
    var maxCompletionTokens: Int?
    var stop: Stop?
    var enableThinking: Bool?

    /// `stop` may be a single string or a list of strings.
    enum Stop: Decodable {
        case one(String)
        case many([String])

        init(from decoder: Decoder) throws {
            let c = try decoder.singleValueContainer()
            if let s = try? c.decode(String.self) { self = .one(s) } else { self = .many(try c.decode([String].self)) }
        }

        var list: [String] {
            switch self {
            case .one(let s): [s]
            case .many(let l): l
            }
        }
    }
}

struct ChatCompletion: Encodable {
    struct Choice: Encodable {
        var index = 0
        var message: ChatMessage
        var finishReason: String
    }
    var id: String
    var object = "chat.completion"
    var created: Int
    var model: String
    var choices: [Choice]
    var usage: UsageBody
}

struct ChatChunk: Encodable {
    struct Delta: Encodable {
        var role: String?
        var content: String?
        var toolCalls: [ToolCallBody]?
    }
    struct Choice: Encodable {
        var index = 0
        var delta: Delta
        var finishReason: String?
    }
    var id: String
    var object = "chat.completion.chunk"
    var created: Int
    var model: String
    var choices: [Choice]
    var usage: UsageBody?
}

struct UsageBody: Encodable {
    struct Details: Encodable { var cachedTokens: Int }
    var promptTokens: Int
    var completionTokens: Int
    var totalTokens: Int
    var promptTokensDetails: Details
}

struct ModelList: Encodable {
    struct Model: Encodable {
        var id: String
        var object = "model"
        var ownedBy = "local"
    }
    var object = "list"
    var data: [Model]
}

struct ErrorBody: Encodable {
    struct Detail: Encodable {
        var message: String
        var type: String
    }
    var error: Detail
}

let jsonEncoder: JSONEncoder = {
    let e = JSONEncoder()
    e.keyEncodingStrategy = .convertToSnakeCase
    return e
}()

let jsonDecoder: JSONDecoder = {
    let d = JSONDecoder()
    d.keyDecodingStrategy = .convertFromSnakeCase
    return d
}()

/// Converts `JSONSerialization` output into plain Swift values that the
/// chat template engine accepts.
func sendableJSON(_ value: Any) -> any Sendable {
    switch value {
    case let v as String: return v
    case let v as NSNumber:
        if CFGetTypeID(v) == CFBooleanGetTypeID() { return v.boolValue }
        return v.doubleValue == v.doubleValue.rounded() ? v.intValue as any Sendable : v.doubleValue
    case let v as [Any]: return v.map(sendableJSON)
    case let v as [String: Any]: return v.mapValues(sendableJSON)
    default: return ""
    }
}

/// OpenAI clients send `arguments` as a JSON string; chat templates want an object.
func templateMessage(_ raw: [String: Any]) -> [String: any Sendable] {
    var message = raw
    if let calls = raw["tool_calls"] as? [[String: Any]] {
        message["tool_calls"] = calls.map { call -> [String: Any] in
            var call = call
            if var function = call["function"] as? [String: Any],
               let args = function["arguments"] as? String,
               let data = args.data(using: .utf8),
               let object = try? JSONSerialization.jsonObject(with: data) {
                function["arguments"] = object
                call["function"] = function
            }
            return call
        }
    }
    if message["content"] is NSNull { message["content"] = "" }
    return message.mapValues(sendableJSON)
}
