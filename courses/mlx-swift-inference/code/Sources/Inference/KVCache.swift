import MLX

/// Keys and values for one attention layer, stored in a buffer that grows in
/// fixed steps so that decoding one token does not copy the whole history.
public final class KVCache {
    public internal(set) var offset = 0
    var keys: MLXArray?
    var values: MLXArray?
    let step = 256

    public init() {}

    /// Appends `[B, kvHeads, L, headDim]` keys and values and returns
    /// everything cached so far, including the new entries.
    public func update(keys newKeys: MLXArray, values newValues: MLXArray) -> (MLXArray, MLXArray) {
        let previous = offset
        let count = newKeys.dim(2)

        if keys == nil || previous + count > keys!.dim(2) {
            let (B, H, _, D) = (newKeys.dim(0), newKeys.dim(1), newKeys.dim(2), newKeys.dim(3))
            let capacity = ((count + step - 1) / step) * step
            let k = MLXArray.zeros([B, H, capacity, D], dtype: newKeys.dtype)
            let v = MLXArray.zeros([B, H, capacity, newValues.dim(3)], dtype: newValues.dtype)
            if let keys, let values {
                self.keys = concatenated([keys[.ellipsis, ..<previous, 0...], k], axis: 2)
                self.values = concatenated([values[.ellipsis, ..<previous, 0...], v], axis: 2)
            } else {
                self.keys = k
                self.values = v
            }
        }

        offset += count
        keys![.ellipsis, previous ..< offset, 0...] = newKeys
        values![.ellipsis, previous ..< offset, 0...] = newValues
        return (keys![.ellipsis, ..<offset, 0...], values![.ellipsis, ..<offset, 0...])
    }

    /// Drops the newest `count` entries. Speculative decoding uses this to
    /// discard rejected draft tokens.
    public func trim(_ count: Int) {
        offset -= min(count, offset)
    }

    /// The arrays that hold the cache, for `eval` and memory accounting.
    public var state: [MLXArray] { [keys, values].compactMap { $0 } }
}
