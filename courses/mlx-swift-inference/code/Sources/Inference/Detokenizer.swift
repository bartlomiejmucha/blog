import Tokenizers

/// Turns a growing list of token ids into text increments.
///
/// One token is not always one piece of text: a multi-byte character can
/// span tokens, and the tokenizer may change how earlier tokens print once
/// it sees the next one. So we decode a window of recent tokens and emit
/// only what is new, holding back a trailing U+FFFD (an incomplete
/// character). The window restarts after each newline to keep decoding cheap.
public struct StreamingDetokenizer {
    let tokenizer: any Tokenizer
    var tokens: [Int] = []
    var segmentStart = 0
    var emitted = ""

    public init(tokenizer: any Tokenizer) {
        self.tokenizer = tokenizer
    }

    public mutating func append(_ token: Int) -> String {
        tokens.append(token)
        let text = tokenizer.decode(tokens: Array(tokens[segmentStart...]))
        if text.hasSuffix("\u{FFFD}") { return "" }
        let delta = String(text.dropFirst(emitted.count))
        emitted = text
        if text.hasSuffix("\n") {
            segmentStart = tokens.count
            emitted = ""
        }
        return delta
    }
}

/// Watches streamed text for stop strings. Text that might be the start of
/// a stop string is held back until it is clear either way.
public struct StopMatcher {
    let stops: [String]
    var pending = ""

    public init(stops: [String]) {
        self.stops = stops.filter { !$0.isEmpty }
    }

    /// Returns text that is safe to emit, and whether a stop string was hit.
    public mutating func feed(_ text: String) -> (String, stopped: Bool) {
        pending += text
        for stop in stops {
            if let range = pending.range(of: stop) {
                let out = String(pending[..<range.lowerBound])
                pending = ""
                return (out, true)
            }
        }
        // Keep the longest suffix that is a prefix of some stop string.
        var keep = 0
        for stop in stops {
            for n in stride(from: min(stop.count - 1, pending.count), to: 0, by: -1)
            where pending.hasSuffix(stop.prefix(n)) {
                keep = max(keep, n)
                break
            }
        }
        let out = String(pending.dropLast(keep))
        pending = String(pending.suffix(keep))
        return (out, false)
    }

    /// Flushes held-back text once generation ends for another reason.
    public mutating func finish() -> String {
        defer { pending = "" }
        return pending
    }
}
