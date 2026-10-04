import MLX

/// Per-layer generation state. Attention layers keep every past key and
/// value. Linear-attention layers keep a fixed-size summary instead.
public protocol LayerCache: AnyObject {
    /// Number of tokens this cache has seen.
    var offset: Int { get }
    /// Arrays to `eval` after a step.
    var state: [MLXArray] { get }
    /// Forget the newest `count` tokens.
    func trim(_ count: Int)
    /// An independent copy that later updates to either side do not affect.
    func copy() -> LayerCache
}

extension KVCache: LayerCache {}

/// State of one Gated DeltaNet layer: the last `kernel - 1` inputs of the
/// causal convolution, plus the `[B, Hv, Dv, Dk]` recurrent matrix.
///
/// The recurrent matrix is a running sum, so tokens cannot be subtracted
/// back out. To support `trim`, the layer can record a snapshot after every
/// token of a step (`recordSnapshots`), and `trim` restores one of them.
public final class LinearCache: LayerCache {
    public private(set) var offset = 0
    var conv: MLXArray?
    var recurrent: MLXArray?
    public var recordSnapshots = false
    var snapshots: [(conv: MLXArray, recurrent: MLXArray)] = []

    public init() {}

    func update(conv: MLXArray, recurrent: MLXArray, count: Int, snapshots: [(MLXArray, MLXArray)]) {
        self.conv = conv
        self.recurrent = recurrent
        self.snapshots = snapshots
        offset += count
    }

    public var state: [MLXArray] { [conv, recurrent].compactMap { $0 } }

    public func trim(_ count: Int) {
        guard count > 0 else { return }
        // snapshots[i] is the state after token i of the last step.
        precondition(count < snapshots.count, "can only trim tokens from the last recorded step")
        let restored = snapshots[snapshots.count - 1 - count]
        conv = restored.conv
        recurrent = restored.recurrent
        offset -= count
        snapshots = []
    }
}

/// The attention caches of several independent sequences, used for one
/// batched decode step. Each sequence keeps its own length and positions.
final class BatchKVCache: LayerCache {
    let caches: [KVCache]
    init(_ caches: [KVCache]) { self.caches = caches }
    var offset: Int { caches.map(\.offset).max() ?? 0 }
    var state: [MLXArray] { caches.flatMap(\.state) }
    func trim(_ count: Int) { caches.forEach { $0.trim(count) } }
    func copy() -> LayerCache { fatalError("batch views are temporary") }
}

/// The linear-attention state of several sequences, stacked along the batch
/// axis for one step and split back afterwards. Every sequence holds the
/// same fixed-size state, so no padding is needed.
final class BatchLinearCache: LayerCache {
    let caches: [LinearCache]
    init(_ caches: [LinearCache]) { self.caches = caches }
    var offset: Int { caches.map(\.offset).max() ?? 0 }
    var state: [MLXArray] { caches.flatMap(\.state) }
    func trim(_ count: Int) { caches.forEach { $0.trim(count) } }
    func copy() -> LayerCache { fatalError("batch views are temporary") }

    var conv: MLXArray { concatenated(caches.map { $0.conv! }, axis: 0) }
    var recurrent: MLXArray { concatenated(caches.map { $0.recurrent! }, axis: 0) }

    func update(conv: MLXArray, recurrent: MLXArray, count: Int) {
        for (i, cache) in caches.enumerated() {
            cache.update(conv: conv[i ..< i + 1], recurrent: recurrent[i ..< i + 1], count: count, snapshots: [])
        }
    }
}

/// Applies RoPE, appends to the cache and runs scaled dot-product attention.
/// `q`, `k`, `v` are `[B, heads, L, headDim]`; the result has q's shape.
///
/// With a `BatchKVCache` every row has its own history length, so rows are
/// rotated and attended one at a time. The projections around this call,
/// which dominate the cost, still run once for the whole batch.
func attend(
    q: MLXArray, k: MLXArray, v: MLXArray, cache: LayerCache?, scale: Float,
    rope: (MLXArray, Int) -> MLXArray
) -> MLXArray {
    let mask: MLXFast.ScaledDotProductAttentionMaskMode = q.dim(2) > 1 ? .causal : .none
    if let batch = cache as? BatchKVCache {
        let rows = batch.caches.enumerated().map { i, c in
            let offset = c.offset
            let (keys, values) = c.update(keys: rope(k[i ..< i + 1], offset), values: v[i ..< i + 1])
            return MLXFast.scaledDotProductAttention(
                queries: rope(q[i ..< i + 1], offset), keys: keys, values: values, scale: scale, mask: mask)
        }
        return concatenated(rows, axis: 0)
    }
    let kv = cache as? KVCache
    let offset = kv?.offset ?? 0
    var (keys, values) = (rope(k, offset), v)
    if let kv {
        (keys, values) = kv.update(keys: keys, values: values)
    }
    return MLXFast.scaledDotProductAttention(
        queries: rope(q, offset), keys: keys, values: values, scale: scale, mask: mask)
}

/// Per-layer views that span the caches of several sequences.
public func batchCaches(_ perSequence: [[LayerCache]]) -> [LayerCache] {
    (0 ..< perSequence[0].count).map { layer in
        if perSequence[0][layer] is KVCache {
            return BatchKVCache(perSequence.map { $0[layer] as! KVCache })
        }
        return BatchLinearCache(perSequence.map { $0[layer] as! LinearCache })
    }
}
