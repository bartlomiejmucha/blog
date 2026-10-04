import Foundation
import Inference
import MLX
import Tokenizers

let directory = URL(filePath: CommandLine.arguments[1])
let mode = CommandLine.arguments[2]  // "plain", "mtp", "bench", "batchbench", "gap", "logits"
let temperature = Float(CommandLine.arguments[3]) ?? 0
let question = "Write a short Python function that checks whether a number is prime, then explain it."

if mode == "logits" {
    // Raw logits for a fixed prompt, for comparison with the Python reference.
    let loaded = try await LoadedModel.load(directory: directory, quantizeBits: nil)
    let ids = MLXArray([9707, 11, 1246, 525, 498, 30, 358, 1079] as [Int32]).reshaped(1, -1)
    try save(arrays: ["logits": loaded.model(ids, caches: nil).asType(.float32)], url: URL(filePath: CommandLine.arguments[4]))
    exit(0)
}
let bits = Int(ProcessInfo.processInfo.environment["QBITS"] ?? "4") ?? 4
let model = try loadQwen35(from: directory, withMTP: true, quantizeBits: bits == 16 ? nil : bits)
let tokenizer = try await AutoTokenizer.from(modelFolder: directory)
let prompt = try tokenizer.applyChatTemplate(
    messages: [["role": "user", "content": question]], tools: nil,
    additionalContext: ["enable_thinking": false])
let eos = Set([tokenizer.eosTokenId, tokenizer.convertTokenToId("<|im_end|>"), tokenizer.convertTokenToId("<|endoftext|>")].compactMap { $0 })
let params = SamplingParameters(temperature: temperature, seed: 7)

if mode == "bench" {
    func time(_ label: String, _ body: () -> Void) {
        body()
        let t0 = Date()
        for _ in 0 ..< 30 { body() }
        print(label, String(format: "%.1f ms", Date().timeIntervalSince(t0) / 30 * 1000))
    }
    let caches = model.makeCaches()
    _ = model(MLXArray(prompt.map(Int32.init)).reshaped(1, -1), caches: caches)
    eval(caches.flatMap(\.state))
    let one = MLXArray([Int32(100)]).reshaped(1, 1)
    let two = MLXArray([Int32(100), Int32(200)]).reshaped(1, 2)
    time("target 1 token") { let l = model(one, caches: caches); eval(l); for c in caches { if let k = c as? KVCache { k.trim(1) } } }
    time("target 2 tokens kernel") { let l = model(two, caches: caches); eval(l)
        for c in caches { if let k = c as? KVCache { k.trim(2) } } }
    time("target 2 tokens snapshots") {
        for case let c as LinearCache in caches { c.recordSnapshots = true }
        let l = model(two, caches: caches); eval(l)
        for case let c as LinearCache in caches { c.recordSnapshots = false }
        for c in caches { c.trim(1) }; for c in caches { if let k = c as? KVCache { k.trim(1) } } }
    let mtp = model.mtp!; let mc = mtp.makeCaches()
    let h = MLXArray.zeros([1, 1, model.config.hiddenSize], dtype: .bfloat16)
    time("mtp head + lm_head") { let o = model.logits(mtp(embeddings: model.embed(one), hidden: h, caches: mc)); eval(argMax(o, axis: -1)); mc[0].trim(1) }
    time("lm_head only") { eval(argMax(model.logits(h), axis: -1)) }
    exit(0)
}
if mode == "batchbench" {
    for B in [1, 2, 4, 8] {
        let ids = (0 ..< B).map { _ -> Int in 0 }
        _ = ids
        let perSeq = (0 ..< B).map { _ -> [LayerCache] in
            let c = model.makeCaches()
            _ = model(MLXArray((0 ..< 64).map { Int32(100 + $0) }).reshaped(1, -1), caches: c)
            eval(c.flatMap(\.state))
            return c
        }
        let views = batchCaches(perSeq)
        let tokens = MLXArray(Array(repeating: Int32(200), count: B)).reshaped(B, 1)
        eval(argMax(model(tokens, caches: views), axis: -1))
        let n = 20
        let t0 = Date()
        for _ in 0 ..< n { eval(argMax(model(tokens, caches: views), axis: -1)) }
        let ms = Date().timeIntervalSince(t0) / Double(n) * 1000
        print("B=\(B): \(String(format: "%.1f", ms)) ms/step, \(String(format: "%.0f", Double(B) * 1000 / ms)) tok/s")
    }
    exit(0)
}
if mode == "perf" {
    // 1. Decode with and without queueing the next step before reading the current token.
    let p = Array(prompt.prefix(16))
    for pipelined in [true, false] {
        let caches = model.makeCaches()
        _ = model(MLXArray(p.map(Int32.init)).reshaped(1, -1), caches: caches)
        var token = MLXArray([Int32(1)]).reshaped(1, 1)
        let n = 100
        let t0 = Date()
        if pipelined {
            var next = argMax(model(token, caches: caches)[0..., -1, 0...], axis: -1).reshaped(1, 1)
            asyncEval(next)
            for _ in 0 ..< n {
                let current = next
                next = argMax(model(current, caches: caches)[0..., -1, 0...], axis: -1).reshaped(1, 1)
                asyncEval(next)
                _ = current.item(Int.self)
            }
        } else {
            for _ in 0 ..< n {
                token = argMax(model(token, caches: caches)[0..., -1, 0...], axis: -1).reshaped(1, 1)
                _ = token.item(Int.self)
            }
        }
        print("decode pipelined=\(pipelined): \(String(format: "%.2f", Date().timeIntervalSince(t0) / Double(n) * 1000)) ms/token")
    }
    // 2. Prefill 512 tokens with the Metal kernel and with plain ops.
    for kernel in [true, false] {
        gatedDeltaUseKernel = kernel
        let ids = MLXArray((0 ..< 512).map { Int32(1000 + $0) }).reshaped(1, -1)
        eval(model(ids, caches: model.makeCaches()))
        let t0 = Date()
        for _ in 0 ..< 3 { let c = model.makeCaches(); eval(model(ids, caches: c)) }
        print("prefill 512 kernel=\(kernel): \(String(format: "%.0f", Date().timeIntervalSince(t0) / 3 * 1000)) ms")
    }
    gatedDeltaUseKernel = true
    // 3. Peak memory after loading.
    print("active memory \(MLX.Memory.activeMemory / 1_000_000) MB, peak \(MLX.Memory.peakMemory / 1_000_000) MB")
    exit(0)
}
if mode == "gap" {
    let toks = try JSONDecoder().decode([Int].self, from: Data(CommandLine.arguments[4].utf8))
    let logits = model(MLXArray((prompt + toks).map(Int32.init)).reshaped(1, -1), caches: nil)[0, -1].asType(.float32)
    let order = argSort(-logits)[..<3]
    for i in 0 ..< 3 { let id = order[i].item(Int.self); print(id, tokenizer.decode(tokens: [id]).debugDescription, logits[id].item(Float.self)) }
    exit(0)
}
var output = [Int]()
let start = Date()
var rate = 0.0
if mode == "mtp" {
    var gen = MTPGenerator(model: model, prompt: prompt, parameters: params, maxTokens: 256)
    while let t = gen.next(), !eos.contains(t) { output.append(t) }
    rate = gen.acceptanceRate
} else {
    for t in TokenGenerator(model: model, prompt: prompt, parameters: params, maxTokens: 256) {
        if eos.contains(t) { break }
        output.append(t)
    }
}
let seconds = Date().timeIntervalSince(start)
print(tokenizer.decode(tokens: output))
print("TOKENS", output)
print(String(format: "%@: %d tokens in %.2fs = %.1f tok/s, acceptance %.2f", mode, output.count, seconds, Double(output.count) / seconds, rate))
