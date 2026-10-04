import Foundation

public struct ToolCall: Sendable, Equatable {
    public var name: String
    /// Arguments as a JSON object string, the form OpenAI clients expect.
    public var arguments: String
}

/// Extracts tool calls from model output.
///
/// Qwen models write calls inside `<tool_call>...</tool_call>`. Qwen3 puts
/// JSON inside (`{"name": ..., "arguments": {...}}`); Qwen3.5 uses XML-like
/// tags (`<function=name><parameter=key>value</parameter></function>`).
/// Both are accepted. Text before the first call is returned as content.
public enum ToolCallParser {
    public static let openTag = "<tool_call>"
    static let closeTag = "</tool_call>"

    public static func parse(_ text: String) -> (content: String, calls: [ToolCall]) {
        guard let first = text.range(of: openTag) else { return (text, []) }
        let content = String(text[..<first.lowerBound]).trimmingCharacters(in: .whitespacesAndNewlines)
        var calls = [ToolCall]()
        var rest = text[first.lowerBound...]
        while let open = rest.range(of: openTag) {
            let afterOpen = rest[open.upperBound...]
            let close = afterOpen.range(of: closeTag)
            let body = String(close.map { afterOpen[..<$0.lowerBound] } ?? afterOpen)
            if let call = parseJSON(body) ?? parseXML(body) { calls.append(call) }
            guard let close else { break }
            rest = afterOpen[close.upperBound...]
        }
        return (content, calls)
    }

    static func parseJSON(_ body: String) -> ToolCall? {
        guard let data = body.trimmingCharacters(in: .whitespacesAndNewlines).data(using: .utf8),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let name = object["name"] as? String
        else { return nil }
        let args = object["arguments"] ?? [String: Any]()
        let encoded = (try? JSONSerialization.data(withJSONObject: args, options: [.sortedKeys])) ?? Data("{}".utf8)
        return ToolCall(name: name, arguments: String(decoding: encoded, as: UTF8.self))
    }

    static func parseXML(_ body: String) -> ToolCall? {
        guard let function = body.firstMatch(of: /<function=([^>\n]+)>/) else { return nil }
        var args = [String: Any]()
        for m in body.matches(of: /<parameter=([^>\n]+)>\n?(.*?)\n?<\/parameter>/.dotMatchesNewlines()) {
            let raw = String(m.2)
            // Values are written as plain text; keep numbers, booleans and
            // JSON objects typed when they parse as JSON.
            if let data = raw.data(using: .utf8),
               let value = try? JSONSerialization.jsonObject(with: data, options: [.fragmentsAllowed]),
               !(value is String) {
                args[String(m.1)] = value
            } else {
                args[String(m.1)] = raw
            }
        }
        let encoded = (try? JSONSerialization.data(withJSONObject: args, options: [.sortedKeys])) ?? Data("{}".utf8)
        return ToolCall(name: String(function.1), arguments: String(decoding: encoded, as: UTF8.self))
    }
}
