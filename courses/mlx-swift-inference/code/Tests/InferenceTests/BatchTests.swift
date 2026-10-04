import MLX
import Testing
@testable import Inference

/// Greedy decoding of several prompts in one batch must match decoding
/// each prompt alone, up to near-ties that rounding can flip.
@Test(arguments: ["qwen3", "qwen35"])
func batchedDecodeMatchesSerial(_ which: String) throws {
    let found = which == "qwen3" ? TestModels.qwen3 : TestModels.qwen35
    try #require(found != nil, "model weights for \(which) not found")
    let dir = found!
    let model: any LanguageModel = which == "qwen3" ? try loadQwen3(from: dir) : try loadQwen35(from: dir, withMTP: false)
    let prompts: [[Int]] = [[9707, 11, 1246, 525], [785, 6722, 315, 9625, 374], [16, 11, 17, 11, 18, 11]]
    let steps = 24

    // Serial reference: logits for each step of each prompt.
    var serial = [[MLXArray]]()
    for p in prompts {
        let caches = model.makeCaches()
        var logits = model(MLXArray(p.map(Int32.init)).reshaped(1, -1), caches: caches)[0..., -1, 0...]
        var rows = [logits]
        for _ in 1 ..< steps {
            let t = argMax(logits, axis: -1).reshaped(1, 1)
            logits = model(t, caches: caches)[0..., -1, 0...]
            rows.append(logits)
        }
        eval(rows)
        serial.append(rows)
    }

    // Batched: prefill each prompt alone, then decode all together, feeding
    // the *serial* tokens so both runs see identical inputs.
    let perSeq = prompts.map { p -> [LayerCache] in
        let c = model.makeCaches()
        _ = model(MLXArray(p.map(Int32.init)).reshaped(1, -1), caches: c)
        return c
    }
    for step in 1 ..< steps {
        let tokens = MLXArray(serial.map { Int32(argMax($0[step - 1], axis: -1).item(Int.self)) }).reshaped(-1, 1)
        let views: [LayerCache] = (0 ..< perSeq[0].count).map { l in
            perSeq[0][l] is KVCache
                ? BatchKVCache(perSeq.map { $0[l] as! KVCache }) as LayerCache
                : BatchLinearCache(perSeq.map { $0[l] as! LinearCache })
        }
        let logits = model(tokens, caches: views)[0..., -1, 0...]
        for i in prompts.indices {
            let diff = abs(logits[i].asType(.float32) - serial[i][step][0].asType(.float32)).max().item(Float.self)
            #expect(diff < 1.0, "\(which) seq \(i) step \(step): max logit diff \(diff)")
        }
    }
}
