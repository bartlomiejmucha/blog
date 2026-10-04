import MLX

extension KVCache {
    /// An independent copy. `update` writes into the key and value buffers
    /// in place, so a stored cache must never be handed out directly.
    public func copy() -> LayerCache {
        let c = KVCache()
        if let keys, let values {
            c.keys = keys[.ellipsis, ..<offset, 0...]
            c.values = values[.ellipsis, ..<offset, 0...]
        }
        c.offset = offset
        return c
    }
}

extension LinearCache {
    /// `update` replaces the arrays instead of writing into them, so sharing
    /// the arrays is safe.
    public func copy() -> LayerCache {
        let c = LinearCache()
        c.update(conv: conv!, recurrent: recurrent!, count: offset, snapshots: [])
        return c
    }
}

/// Keeps the caches of recent requests so a follow-up that starts with the
/// same tokens (the next turn of a chat, a shared system prompt) skips
/// prefilling them.
///
/// Matching is on whole entries: an entry is used only if all of its
/// tokens are a prefix of the new prompt. Attention caches could be trimmed
/// to a shorter common prefix, but linear-attention state cannot, so this
/// rule works for both kinds of layer.
///
/// What to store matters as much as how to match. Chat templates often
/// re-render earlier turns differently from how they were generated (Qwen3.5
/// drops the empty think block from past answers), so the state at the end
/// of a reply rarely matches the next prompt. The engine instead stores the
/// state at the start of the last `<|im_start|>` in the prompt: everything
/// before it is history that the next turn repeats verbatim.
final class PromptCache {
    struct Entry {
        var tokens: [Int]
        var caches: [LayerCache]
    }

    let capacity: Int
    private var entries: [Entry] = []   // most recently used last

    init(capacity: Int) {
        self.capacity = capacity
    }

    /// Returns caches to start from and how many prompt tokens they cover.
    /// At least one prompt token is always left to run, because generation
    /// needs the logits of the last prompt position.
    func lookup(prompt: [Int], model: any LanguageModel) -> (caches: [LayerCache], count: Int) {
        let best = entries.indices
            .filter { entries[$0].tokens.count < prompt.count && prompt.starts(with: entries[$0].tokens) }
            .max { entries[$0].tokens.count < entries[$1].tokens.count }
        guard let index = best, capacity > 0 else { return (model.makeCaches(), 0) }

        let entry = entries.remove(at: index)
        entries.append(entry)
        return (entry.caches.map { $0.copy() }, entry.tokens.count)
    }

    func store(tokens: [Int], caches: [LayerCache]) {
        guard capacity > 0, caches.first?.offset == tokens.count else { return }
        // A new entry supersedes any entry it extends.
        entries.removeAll { tokens.starts(with: $0.tokens) }
        entries.append(Entry(tokens: tokens, caches: caches))
        if entries.count > capacity { entries.removeFirst() }
    }
}
