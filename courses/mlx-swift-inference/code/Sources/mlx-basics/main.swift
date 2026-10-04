// Lessons 3 and 4: the MLX Swift building blocks, one function per idea.
// Run: xcodebuild build -scheme mlx-basics ... && DerivedData/Build/Products/Release/mlx-basics
import Foundation
import MLX
import MLXNN

func arraysAndShapes() {
    let a = MLXArray([1, 2, 3, 4, 5, 6] as [Float]).reshaped(2, 3)
    print(a.shape, a.dtype)              // [2, 3] float32

    let b = MLXArray([10, 20, 30] as [Float])
    print(a + b)                          // b is broadcast across both rows

    let m = MLXArray.ones([3, 4])
    print(matmul(a, m).shape)             // [2, 4]

    print(a[0])                           // first row
    print(a[0..., 1])                     // second column
    print(a[.ellipsis, ..<2])             // first two columns
}

func dtypes() {
    let x = MLXArray([1.5, -2.25, 3.0] as [Float])
    let h = x.asType(.bfloat16)
    print(h.dtype, h.nbytes)              // bfloat16, 6 bytes: 2 per element
    // bfloat16 keeps float32's range but only ~3 significant digits.
    print(MLXArray(Float(1000.1)).asType(.bfloat16).item(Float.self))  // 1000.0
}

func lazyEvaluation() {
    let a = MLXArray.ones([4096, 4096])
    eval(matmul(a, a))                    // warm up: the first call also sets up kernels
    let t0 = Date()
    let b = matmul(a, a) + 1              // builds a graph; nothing runs yet
    let built = Date()
    eval(b)                               // now the GPU does the work
    let done = Date()
    print(String(format: "build %.3f ms, eval %.1f ms",
                 built.timeIntervalSince(t0) * 1000, done.timeIntervalSince(built) * 1000))
    // item() and printing also force evaluation.
    print(b[0, 0].item(Float.self))       // 4097.0
}

func asyncEvaluation() {
    let a = MLXArray.ones([2048, 2048])
    var x = a
    for _ in 0 ..< 3 { x = matmul(x, a) / 2048 }
    asyncEval(x)                          // queue the work and return at once
    // ... the CPU is free to prepare the next step here ...
    print(x[0, 0].item(Float.self))       // blocks only if the GPU is not done yet
}

/// A tiny two-layer network. Property keys are the names checkpoints use.
final class TinyMLP: Module, UnaryLayer {
    @ModuleInfo(key: "up_proj") var up: Linear
    @ModuleInfo(key: "down_proj") var down: Linear

    init(dims: Int, hidden: Int) {
        _up.wrappedValue = Linear(dims, hidden, bias: false)
        _down.wrappedValue = Linear(hidden, dims, bias: false)
    }

    func callAsFunction(_ x: MLXArray) -> MLXArray {
        down(silu(up(x)))
    }
}

func modulesAndParameters() throws {
    let mlp = TinyMLP(dims: 8, hidden: 32)
    for (name, array) in mlp.parameters().flattened() {
        print(name, array.shape)          // down_proj.weight [8, 32], up_proj.weight [32, 8]
    }
    // Loading weights is a dictionary update keyed by those names.
    let weights: [String: MLXArray] = [
        "up_proj.weight": MLXArray.zeros([32, 8]),
        "down_proj.weight": MLXArray.zeros([8, 32]),
    ]
    try mlp.update(parameters: ModuleParameters.unflattened(weights), verify: [.all])
    print(mlp(MLXArray.ones([1, 8])).sum().item(Float.self))  // 0.0
}

func quantizedLinear() {
    let linear = Linear(256, 512, bias: false)
    let q = QuantizedLinear(linear, groupSize: 64, bits: 4)
    print(q.weight.shape, q.weight.dtype)  // [512, 32] uint32: 8 four-bit values per word
    print(q.scales.shape)                  // [512, 4]: one scale per group of 64
    let x = MLXArray.ones([1, 256])
    let error = abs(q(x) - linear(x)).max().item(Float.self)
    print("max error from 4-bit:", error)
}

func compiledFunctions() {
    // Elementwise steps run as separate kernels, each one reading and
    // writing the whole array...
    let gate = MLXRandom.normal([1, 4096]).asType(.bfloat16)
    let up = MLXRandom.normal([1, 4096]).asType(.bfloat16)
    let plain = silu(gate) * up
    // ...compile() traces the function once and fuses them into one kernel.
    let fused = compile(shapeless: true) { (g: MLXArray, u: MLXArray) in silu(g) * u }
    let diff = abs(plain.asType(.float32) - fused(gate, up).asType(.float32)).max()
    print("max difference:", diff.item(Float.self))   // 0.0: same math, fewer memory round trips
}

func fastKernels() {
    let x = MLXRandom.normal([1, 8, 16, 64])          // [batch, heads, tokens, headDim]
    let w = MLXArray.ones([64])
    let n = MLXFast.rmsNorm(x, weight: w, eps: 1e-6)
    let r = MLXFast.RoPE(n, dimensions: 64, traditional: false, base: 10_000, scale: 1, offset: 0)
    let out = MLXFast.scaledDotProductAttention(
        queries: r, keys: r, values: x, scale: 1 / 8, mask: .causal)
    print(out.shape)                                   // [1, 8, 16, 64]
}

func customKernel() {
    // One GPU thread per element. MLX generates the function signature from
    // the input and output names; the body is plain Metal.
    let kernel = MLXFast.metalKernel(
        name: "scaled_add",
        inputNames: ["a", "b"],
        outputNames: ["out"],
        source: """
            uint i = thread_position_in_grid.x;
            out[i] = a[i] * 2.0 + b[i];
            """)
    let a = MLXArray([1, 2, 3, 4] as [Float])
    let b = MLXArray([10, 10, 10, 10] as [Float])
    let out = kernel([a, b], grid: (4, 1, 1), threadGroup: (4, 1, 1),
                     outputShapes: [[4]], outputDTypes: [.float32])
    print(out[0])                                      // [12, 14, 16, 18]
}

arraysAndShapes()
dtypes()
lazyEvaluation()
asyncEvaluation()
try modulesAndParameters()
quantizedLinear()
compiledFunctions()
fastKernels()
customKernel()
