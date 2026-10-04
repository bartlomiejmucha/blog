# -*- coding: utf-8 -*-
"""Part I — Foundations. Lessons 1-5."""
from codeblocks import block, source

def fig(fid, title, sub, body=""):
    return ('<div class="figure" id="%s">'
            '<p class="figure-title">%s</p>'
            '<p class="figure-sub">%s</p>%s</div>') % (fid, title, sub, body)

LESSONS = []

# ------------------------------------------------------------------ 1
LESSONS.append(dict(
    part="Part I · Foundations",
    title="What an inference server does",
    blurb="Before writing code, see the whole machine: what happens between an HTTP request arriving and the last token leaving, and which part of the code owns each step.",
    viz=True,
    goals=[
        "Name the stages a chat request passes through inside an inference server",
        "Tell time to first token apart from decode speed, and say what each one depends on",
        "Find your way around the companion package you will build",
        "Run the finished server and talk to it with curl",
    ],
    recap="An inference server turns chat messages into tokens, runs the model once over the prompt (prefill) and then once per new token (decode), and streams text back as it goes. The hard parts are not the HTTP: they are keeping one GPU busy for many clients, reusing work between requests, and making each decode step cheap.",
    sections=[
        dict(title="The job", body="""
<p>A language model is a function: give it a list of token ids, and it returns a score for every possible next token. That is all the model does. Everything else a product like ChatGPT does around it, from accepting messages over HTTP to streaming words back, is the job of an <strong>inference server</strong>.</p>
<p>In this course you build one from scratch, in Swift, on Apple's MLX framework. By the end it will:</p>
<ul>
<li>load Qwen3 and Qwen3.5 checkpoints straight from Hugging Face, dense and mixture-of-experts, quantizing them on the fly;</li>
<li>run them with model code you wrote yourself, checked against the Python reference implementation;</li>
<li>speak the OpenAI Chat Completions API, including streaming and tool calls, so existing clients work unchanged;</li>
<li>serve many clients from one GPU, with a request queue, cancellation, prompt caching and continuous batching;</li>
<li>decode faster with <strong>speculative decoding</strong>, using the multi-token-prediction (MTP) head that ships inside every Qwen3.5 checkpoint.</li>
</ul>
<p>This lesson is the map. Each stage you see here gets one or more lessons of its own later.</p>
"""),
        dict(title="The life of a request", body="""
<p>Follow one request through the finished server. A client sends:</p>
""" + block('''curl localhost:8080/v1/chat/completions -H 'content-type: application/json' -d '{
  "messages": [{"role": "user", "content": "Why is the sky blue?"}],
  "stream": true
}' ''', "shell") + """
<p>The list says what each stage does and where its code lives; the diagram after it lets you step through them in order.</p>
<ol>
<li><strong>HTTP layer</strong> (<code>Sources/serve</code>). Hummingbird parses the JSON body. Nothing here touches the model.</li>
<li><strong>Chat template</strong>. The messages are rendered into one string with the model's own template, for example <code>&lt;|im_start|&gt;user\\nWhy is the sky blue?&lt;|im_end|&gt;\\n&lt;|im_start|&gt;assistant\\n</code>, and tokenized into integers.</li>
<li><strong>Queue</strong>. The token list goes into the engine's inbox. If the inbox is full, the client gets HTTP 429 right away instead of waiting forever.</li>
<li><strong>Prefill</strong>. A dedicated worker thread runs the model over the whole prompt in one pass. This fills the caches and produces the first token.</li>
<li><strong>Decode loop</strong>. The worker feeds each new token back in, one forward pass per token, until an end-of-turn token or the length limit.</li>
<li><strong>Detokenize and stream</strong>. Token ids become text, and each piece is sent to the client as a server-sent event while the next token is being computed.</li>
</ol>
""", figure=fig("viz-lifecycle", "Life of a request",
                "Step through the stages. The highlighted box is where the request is now; the line under it says what the client sees at that moment.")),
        dict(title="Two numbers: time to first token and decode speed", body="""
<p>Users judge a chat server by two things, and they come from different parts of the pipeline.</p>
<p><strong>Time to first token (TTFT)</strong> is the wait before any text appears. It is dominated by prefill: the model must read the whole prompt before it can say anything. A long system prompt or a long chat history makes it worse. Prompt caching (Lesson 14) attacks it by skipping prompt tokens the server has already processed.</p>
<p><strong>Decode speed</strong>, in tokens per second, is how fast text streams once it starts. Each new token costs one full forward pass, and as Lesson 2 shows, that pass is limited by how fast the chip can read the weights from memory, not by arithmetic. Quantization (Lesson 5), speculative decoding (Lessons 18 and 19) and batching (Lesson 15) all attack it from different angles.</p>
<p>A server also has a third number its operator cares about: <strong>throughput</strong>, the total tokens per second across all clients. Batching raises throughput, sometimes at the cost of each client's own decode speed. Keep the three apart; most performance discussions go wrong by mixing them up.</p>
<div class="note"><p class="text-sm">Concrete numbers from the finished server on a base M1 with 8 GB: Qwen3.5-0.8B with 4-bit weights decodes at about 90 tokens per second, and a 1,570-token prompt takes about 3.2 seconds to answer the first time and under 1 second on the next turn, when the prompt cache hits.</p></div>
"""),
        dict(title="The companion package", body="""
<p>All code in this course lives in one Swift package, <code>QwenServe</code>, which you can download from the course home page. Every listing in the lessons is cut directly from it at build time, so what you read is what compiles. The layout:</p>
<table>
<tr><th>Path</th><th>What it is</th><th>Lessons</th></tr>
<tr><td><code>Sources/mlx-basics</code></td><td>small runnable examples of MLX itself</td><td>3, 4</td></tr>
<tr><td><code>Sources/Inference/Qwen3*.swift</code>, <code>Loader.swift</code></td><td>Qwen3 config, model and weight loading</td><td>5, 7, 8</td></tr>
<tr><td><code>Detokenizer.swift</code>, <code>LoadedModel.swift</code></td><td>chat templates, streaming text, stop strings</td><td>6</td></tr>
<tr><td><code>KVCache.swift</code>, <code>Generator.swift</code>, <code>Sampler.swift</code></td><td>the generation loop</td><td>9, 10</td></tr>
<tr><td><code>Sources/serve</code></td><td>the HTTP server</td><td>11, 12, 21</td></tr>
<tr><td><code>Engine.swift</code>, <code>PromptCache.swift</code>, <code>BatchEngine.swift</code></td><td>scheduling, caching, batching</td><td>13, 14, 15</td></tr>
<tr><td><code>SwitchLayers.swift</code></td><td>mixture-of-experts layers</td><td>16</td></tr>
<tr><td><code>Qwen35*.swift</code>, <code>GatedDelta.swift</code>, <code>LayerCache.swift</code></td><td>the Qwen3.5 hybrid architecture</td><td>17</td></tr>
<tr><td><code>MTPHead.swift</code>, <code>MTPGenerator.swift</code></td><td>speculative decoding with MTP</td><td>18, 19</td></tr>
<tr><td><code>Sources/infer</code></td><td>a command-line tool for experiments and benchmarks</td><td>8, 19, 20</td></tr>
<tr><td><code>Tests/InferenceTests</code></td><td>unit tests and model-backed checks</td><td>throughout</td></tr>
</table>
<p>You can read the course in order and rebuild the package file by file, or download it, run it first, and then read the lessons to understand each part. Both work.</p>
"""),
        dict(title="Run the finished server", body="""
<p>You need a Mac with Apple Silicon, Xcode, and Python only for the download tool. Fetch a model and build the server:</p>
""" + block('''# 1. A model. The original checkpoint, because it still contains the MTP head.
pip install -U huggingface_hub
hf download Qwen/Qwen3.5-0.8B --local-dir models/Qwen3.5-0.8B

# 2. Build in Release. xcodebuild, not "swift build": only Xcode's build
#    system compiles MLX's Metal shaders (Lesson 3).
cd code
xcodebuild build -scheme serve -configuration Release \\
  -destination 'platform=OS X' -derivedDataPath DerivedData

# 3. Run it. --bits 8 quantizes to 8-bit on load; Lesson 19 explains why
#    8-bit is the sweet spot for speculative decoding on an M1.
DerivedData/Build/Products/Release/serve ../models/Qwen3.5-0.8B --bits 8 --port 8080''', "shell") + """
<p>In another terminal:</p>
""" + block('''curl -s localhost:8080/v1/chat/completions -H 'content-type: application/json' \\
  -d '{"messages":[{"role":"user","content":"Name three planets."}],"temperature":0}'
# {"choices":[{"message":{"role":"assistant","content":"Earth, Mars, and Jupiter."},
#   "finish_reason":"stop",...}],"usage":{"prompt_tokens":19,"completion_tokens":7,...}}''', "shell") + """
<p>Any OpenAI-compatible client works too: point its base URL at <code>http://localhost:8080/v1</code>. Now you know what you are building. The next lesson explains the single most important fact about running it fast.</p>
"""),
    ],
    exercises=[
        dict(type="order", prompt="<p>Put the stages of a streamed chat request in order.</p>",
             items=["Render messages with the chat template and tokenize",
                    "Put the request in the engine's inbox",
                    "Prefill: run the model over the whole prompt",
                    "Decode: one forward pass per new token",
                    "Detokenize each token and send it as a server-sent event"],
             explain="<p>Template and tokenize first, because the engine only deals in token ids. The queue sits between the HTTP layer and the single worker. Prefill produces the first token; decode produces the rest; detokenizing and streaming happen as each token appears.</p>"),
        dict(type="mcq", prompt="<p>A user complains that answers take five seconds to <em>start</em> appearing, though they stream quickly afterwards. Which stage is the first suspect?</p>",
             options=["Decode", "Prefill", "Detokenization", "JSON encoding"], answer=1,
             explain="<p>The wait before the first token is time to first token, and it is dominated by prefill: the model must process the whole prompt first. Long system prompts and chat histories make it worse. Fast streaming afterwards means decode is fine.</p>"),
        dict(type="multi", prompt="<p>Which of these raise <strong>throughput</strong> (total tokens per second across all clients)? Select all that apply.</p>",
             options=["Batching several requests into each decode step",
                      "Reading the weights from memory faster",
                      "A shorter HTTP route name",
                      "Reusing cached prompt work between requests"], answer=[0, 1, 3],
             explain="<p>Batching amortizes each weight read over several sequences; faster memory reads speed up every step; prompt caching removes prefill work entirely. The route name is irrelevant.</p>"),
        dict(type="mcq", prompt="<p>Why does the course build with <code>xcodebuild</code> instead of <code>swift build</code>?</p>",
             options=["swift build cannot link Swift packages",
                      "Only Xcode's build system compiles MLX's Metal shaders",
                      "xcodebuild produces smaller binaries",
                      "Hummingbird requires Xcode"], answer=1,
             explain="<p>MLX's GPU kernels are Metal shaders. SwiftPM on the command line cannot compile them into the library MLX loads at run time, so the build must go through Xcode's build system.</p>"),
    ],
))

# ------------------------------------------------------------------ 2
LESSONS.append(dict(
    part="Part I · Foundations",
    title="Apple Silicon and the memory-bandwidth bound",
    blurb="Generating one token means reading every weight of the model once. On a Mac that makes memory bandwidth, not compute, the speed limit, and it explains almost every design choice in this course.",
    viz=True,
    goals=[
        "Estimate a model's decode speed from its size and the chip's memory bandwidth",
        "Explain why decode is bandwidth-bound and prefill is compute-bound",
        "Say what unified memory changes, and what it does not",
        "Explain why MLX is a good fit for an inference server on a Mac",
    ],
    recap="Decoding one token reads all the weights once and does about two floating-point operations per weight. That is far too little arithmetic per byte to keep the GPU busy, so decode speed is roughly memory bandwidth divided by model size. Prefill processes many tokens per weight read and is limited by compute instead. Shrinking the bytes (quantization) or sharing each read across more tokens (batching, speculative decoding) are the levers.",
    sections=[
        dict(title="What one token costs", body="""
<p>Lesson 1 said each new token costs one forward pass. Look at what that pass does. Almost all of a transformer's work is matrix-vector multiplication: a vector for the current token is multiplied by weight matrices, layer after layer. For each weight, the GPU must</p>
<ol>
<li>load the weight from memory, and</li>
<li>do one multiply and one add with it: 2 floating-point operations.</li>
</ol>
<p>So decoding one token with a model of <code>N</code> parameters moves about <code>N × bytes per weight</code> bytes and does about <code>2N</code> operations. For Qwen3.5-0.8B with 4-bit weights, that is roughly 0.45 GB read and 1.6 billion operations per token.</p>
<p>Which of the two is the bottleneck depends on the chip. A base M1 can read memory at about 68 GB/s (we measured 52 GB/s achieved by MLX's quantized kernel) and do about 1.45 trillion float32 operations per second (measured with a 4096×4096 matrix multiply). Reading 0.45 GB takes about 8.7 ms at 52 GB/s. Doing 1.6 billion operations takes about 1.1 ms. <strong>The GPU spends most of each step waiting for memory.</strong></p>
"""),
        dict(title="Arithmetic intensity", body="""
<p>The general tool here is <strong>arithmetic intensity</strong>: operations performed per byte moved. Every chip has a balance point, its peak operations per second divided by its bandwidth. For the M1, about 1.45 TFLOPS / 60 GB/s ≈ 24 operations per byte. Work below that is <em>bandwidth-bound</em>; work above it is <em>compute-bound</em>.</p>
<table>
<tr><th>Work</th><th>Operations per weight byte</th><th>Bound by</th></tr>
<tr><td>Decode, 4-bit weights, 1 sequence</td><td>2 ops / 0.5 byte = 4</td><td>bandwidth</td></tr>
<tr><td>Decode, 8 sequences batched</td><td>8 × 4 = 32</td><td>roughly balanced</td></tr>
<tr><td>Prefill, 500-token prompt</td><td>500 × 4 = 2,000</td><td>compute</td></tr>
</table>
<p>Prefill multiplies a whole matrix of token vectors by each weight matrix, so each weight that is read is used hundreds of times. That is why a 512-token prefill takes about 0.75 s on the M1, not 512 × 11 ms ≈ 5.6 s.</p>
<p>The decode row is the important one. Any technique that does more useful work per weight read is a direct speed-up: quantization shrinks the bytes; batching serves several sequences per read (Lesson 15); speculative decoding checks several tokens of one sequence per read (Lessons 18 and 19). The rest of this course keeps coming back to this table.</p>
"""),
        dict(title="Estimate it yourself", body="""
<p>The rule of thumb: <strong>decode tokens per second ≈ achievable bandwidth ÷ bytes read per token</strong>. Achievable bandwidth is usually 70–85% of the advertised figure. Bytes per token is the weight size, plus a little for the KV cache, which grows with context.</p>
<p>Try it below. On the M1, the 0.8B model at 4 bits gives a ceiling of about 113 tokens per second; the finished server reaches about 90. The gap is real work the rule ignores: the 248,000-row output projection, attention over the cache, dozens of small kernel launches per layer, and CPU time between steps. Lesson 20 measures each of these.</p>
""", figure=fig("viz-bandwidth", "Decode speed ceiling",
                "Pick a chip, a model size and a weight precision. The bar is bandwidth ÷ bytes per token, at 75% of the advertised bandwidth.")),
        dict(title="Unified memory", body="""
<p>On a PC with a discrete GPU, the model lives in the GPU's own memory, and anything the CPU produces must be copied across a PCIe bus. Apple Silicon has <strong>unified memory</strong>: CPU and GPU share the same physical RAM. Three consequences matter for us:</p>
<ul>
<li><strong>No copies.</strong> An array written by the CPU (token ids, a sampled token) is visible to the GPU without a transfer. MLX arrays are not tied to a device; you choose where an operation runs, not where data lives.</li>
<li><strong>Model size is limited by RAM.</strong> A 16 GB Mac can hold models that would not fit on a 12 GB graphics card. But macOS keeps part of RAM for itself and caps how much the GPU may use by default, so plan on roughly two thirds of RAM for weights and caches.</li>
<li><strong>Bandwidth is shared.</strong> The same memory system serves the CPU, the GPU and everything else running. A busy browser can slow decode measurably. Benchmark on a quiet machine.</li>
</ul>
"""),
        dict(title="Why MLX", body="""
<p>MLX is Apple's array framework for machine learning on Apple Silicon. It has a NumPy-like API in Python, C++ and Swift, and it was designed around unified memory. For an inference server it gives us:</p>
<ul>
<li><strong>Metal kernels for the hot paths</strong>: quantized matrix multiplication, fused attention, RMSNorm and RoPE, all tuned for Apple GPUs.</li>
<li><strong>Lazy evaluation</strong>: operations build a graph that runs when a result is needed. That lets you queue the next step on the GPU while the CPU does other work (Lesson 3).</li>
<li><strong>A native Swift API</strong>, so the model, the scheduler and the HTTP server are one process in one language with no Python runtime.</li>
<li><strong>Custom kernels</strong> written inline in Metal when nothing built-in fits. Lesson 17 writes one for Qwen3.5's linear attention.</li>
</ul>
<p>The alternatives are worth knowing. llama.cpp is a mature C++ engine with its own file format (GGUF). Core ML targets the Neural Engine but is awkward for autoregressive generation. The Python <code>mlx-lm</code> package is the reference this course checks its numbers against. Building on raw MLX Swift is the right choice here because the goal is to understand and control every part.</p>
"""),
    ],
    exercises=[
        dict(type="numeric", prompt="<p>An 8-billion-parameter model is stored with 4-bit weights (ignore scales). The chip reads memory at 120 GB/s. What is the decode ceiling in tokens per second?</p>",
             answer=30, tolerance=0.5, placeholder="tokens/s",
             explain="<p>8 × 10<sup>9</sup> weights × 0.5 bytes = 4 GB per token. 120 GB/s ÷ 4 GB = 30 tokens per second. Real systems land somewhat below this.</p>"),
        dict(type="mcq", prompt="<p>Why is prefill much faster per token than decode?</p>",
             options=["Prefill skips the attention layers",
                      "Each weight read during prefill is used for every prompt token, so it is compute-bound instead of bandwidth-bound",
                      "Prefill uses a smaller model",
                      "Prefill runs on the Neural Engine"], answer=1,
             explain="<p>During prefill the whole prompt is multiplied by each weight matrix at once. One read serves hundreds of tokens, so arithmetic, not memory, becomes the limit.</p>"),
        dict(type="numeric", prompt="<p>A chip does 4 TFLOPS and reads 200 GB/s. What is its balance point in operations per byte?</p>",
             answer=20, tolerance=0.1, placeholder="ops/byte",
             explain="<p>4 × 10<sup>12</sup> ÷ 200 × 10<sup>9</sup> = 20 operations per byte. Single-sequence decode at about 4 ops/byte sits far below it, so it is bandwidth-bound.</p>"),
        dict(type="multi", prompt="<p>Which statements about unified memory are true? Select all that apply.</p>",
             options=["CPU and GPU can use the same arrays without copying",
                      "The GPU can always use 100% of RAM",
                      "Other apps compete for the same memory bandwidth",
                      "Model size is limited by system RAM, not a separate GPU memory"], answer=[0, 2, 3],
             explain="<p>Unified memory removes copies and the separate VRAM limit, but macOS caps the GPU's share by default and the bandwidth is shared with everything else.</p>"),
    ],
))

# ------------------------------------------------------------------ 3
LESSONS.append(dict(
    part="Part I · Foundations",
    title="MLX Swift basics",
    blurb="Set up the package, then learn the four ideas you will use on every page that follows: arrays and shapes, dtypes, lazy evaluation, and asynchronous evaluation.",
    viz=False,
    goals=[
        "Create a Swift package that depends on MLX and build it correctly",
        "Create, reshape, index and broadcast MLXArrays",
        "Explain bfloat16 and why models use it",
        "Explain lazy evaluation and use eval, item and asyncEval deliberately",
        "Benchmark only Release builds, and know why",
    ],
    recap="MLX arrays are lazy: operations record a graph, and work happens on eval, item, or printing. asyncEval starts the work without waiting, which lets the CPU prepare the next step while the GPU runs. Build with xcodebuild so the Metal shaders are compiled, and measure only Release builds.",
    sections=[
        dict(title="The package", body="""
<p>Everything lives in one Swift package. Here is its manifest. The dependency versions are pinned exactly, because MLX numbers can shift slightly between releases and you want the results in this course to reproduce:</p>
""" + source("Package.swift") + """
<ul>
<li><code>mlx-swift</code> provides <code>MLX</code> (arrays and operations, including the fast fused kernels), <code>MLXNN</code> (layers) and more. Version 0.32.3 bundles MLX core 0.32.2. That matters when you compare against Python (Lesson 8).</li>
<li><code>swift-transformers</code> provides Hugging Face tokenizers and chat-template rendering (Lesson 6).</li>
<li><code>hummingbird</code> is the HTTP server (Lesson 11).</li>
</ul>
<p>Build with Xcode's build system. MLX's GPU kernels are Metal shaders, and command-line SwiftPM cannot compile them into the library MLX loads at run time; a <code>swift build</code> binary fails when it first touches the GPU.</p>
""" + block('''xcodebuild build -scheme mlx-basics -configuration Release \\
  -destination 'platform=OS X' -derivedDataPath DerivedData
DerivedData/Build/Products/Release/mlx-basics''', "shell")),
        dict(title="Arrays, shapes and broadcasting", body="""
<p>An <code>MLXArray</code> is an n-dimensional array with a shape and a dtype. If you have used NumPy or PyTorch, the operations will look familiar:</p>
""" + source("Sources/mlx-basics/main.swift", "func arraysAndShapes") + """
<p>Two rules carry most of the weight:</p>
<ul>
<li><strong>Broadcasting.</strong> When shapes differ, size-1 or missing leading dimensions are stretched to match. <code>[2, 3] + [3]</code> adds the vector to each row. Models use this constantly: adding a bias, scaling by a norm weight.</li>
<li><strong>Indexing.</strong> <code>a[0..., 1]</code> means "all rows, column 1"; <code>.ellipsis</code> stands for "all leading dimensions", so <code>x[.ellipsis, ..&lt;2]</code> takes the first two entries of the last axis whatever the rank. Negative indices count from the end: <code>logits[0..., -1, 0...]</code> is the last position of every sequence, which you will write in every generation loop.</li>
</ul>
<p>Model tensors in this course follow one convention: <code>[B, L, D]</code> for activations (batch, sequence length, hidden size) and <code>[B, heads, L, headDim]</code> inside attention.</p>
"""),
        dict(title="dtypes: why bfloat16", body="""
""" + source("Sources/mlx-basics/main.swift", "func dtypes") + """
<p>Model weights and activations are usually stored in <strong>bfloat16</strong>: 16 bits with float32's 8-bit exponent but only 7 bits of mantissa. It covers the same range as float32, so huge or tiny values do not overflow, but it keeps only about three significant decimal digits: 1000.1 becomes 1000.0.</p>
<p>Half the bytes means half the memory traffic, and Lesson 2 showed that memory traffic is the speed limit. The cost is precision, and you will meet it again: when comparing your model with the Python reference, differences show up in the last bfloat16 digit, and occasionally flip which of two near-equal tokens wins (Lesson 8). Places where precision matters, such as softmax and the linear-attention state, compute in float32 and convert back.</p>
"""),
        dict(title="Lazy evaluation", body="""
<p>This is the most important idea in MLX. Operations do not compute anything when you call them. They record a node in a graph and return immediately. The work runs when a result is actually needed:</p>
""" + source("Sources/mlx-basics/main.swift", "func lazyEvaluation") + """
<p>On the M1 this prints about <code>build 0.04 ms, eval 94 ms</code>: building the graph for a 4096×4096 matrix multiply is instant, and the GPU work happens inside <code>eval</code>. Evaluation is triggered by</p>
<ul>
<li><code>eval(...)</code>, explicitly;</li>
<li><code>item()</code>, which reads a scalar back to Swift;</li>
<li>printing an array.</li>
</ul>
<p>Laziness lets MLX fuse and schedule work, and it lets you build a whole forward pass before anything runs. It also has two traps. First, a graph that is never evaluated keeps growing: in a generation loop you must <code>eval</code> the caches regularly, or each step drags the entire history along. Second, a stray <code>item()</code> in a hot loop forces the CPU to wait for the GPU at that point. Lesson 19 finds exactly this bug in the speculative decoder and removes three of its four waits.</p>
"""),
        dict(title="Asynchronous evaluation", body="""
""" + source("Sources/mlx-basics/main.swift", "func asyncEvaluation") + """
<p><code>asyncEval</code> starts evaluating and returns at once. The CPU can keep working, usually building the graph for the next step, while the GPU computes. Reading the result later blocks only if the GPU has not finished.</p>
<p>The generation loop in Lesson 9 is built around this. Before handing token <em>n</em> to the caller, it queues the forward pass for token <em>n+1</em>, so the CPU-side work of detokenizing and streaming token <em>n</em> overlaps with GPU work. On the M1 that saves about 1.2 ms per token, roughly 11%, measured in Lesson 20.</p>
"""),
        dict(title="Measure Release builds only", body="""
<p>MLX's C++ core is compiled as part of your package. In a Debug build it is compiled without optimization, and the CPU side of every operation, from building graphs to dispatching kernels, becomes several times slower. On the M1 the same Qwen3.5 decode runs at 36 tokens per second in Debug and 89 in Release.</p>
<p>The GPU kernels are identical in both, so Debug builds are fine for checking correctness. But every speed number in this course comes from a Release build, and any number you measure should too. While writing this course, early speculative-decoding results that looked like a 1.4× win in Debug turned out to be a slowdown in Release, because Debug overhead had hidden what the GPU was really doing.</p>
"""),
    ],
    exercises=[
        dict(type="mcq", prompt="<p>You run <code>let y = matmul(x, w)</code> and then read <code>y.shape</code>. Has the GPU multiplied the matrices yet?</p>",
             options=["Yes, every operation runs immediately",
                      "No. The shape is known from the graph; the multiply runs on eval, item or print",
                      "Only if x is on the GPU",
                      "Only in Release builds"], answer=1,
             explain="<p>Shapes are computed when the graph node is created. The values are computed only when something forces evaluation.</p>"),
        dict(type="fill", prompt="<p>Which function starts evaluating an array in the background and returns immediately?</p>",
             answer=["asyncEval", "asyncEval()", "MLX.asyncEval"], placeholder="function name",
             explain="<p><code>asyncEval</code> queues the work and returns. A later read of the result blocks only if the GPU is not done.</p>"),
        dict(type="numeric", prompt="<p>An array of 1,000,000 bfloat16 values. How many megabytes is it (1 MB = 10<sup>6</sup> bytes)?</p>",
             answer=2, tolerance=0.01, placeholder="MB",
             explain="<p>bfloat16 is 2 bytes per value: 2,000,000 bytes = 2 MB. In float32 it would be 4 MB.</p>"),
        dict(type="mcq", prompt="<p>A generation loop appends to a KV cache every step but never calls eval on it. What goes wrong?</p>",
             options=["Nothing, MLX evaluates automatically each step",
                      "The graph keeps growing, so each step carries the whole history of operations and gets slower",
                      "The cache is silently discarded",
                      "The program does not compile"], answer=1,
             explain="<p>Unevaluated arrays are graphs. Without regular evaluation the cache becomes a chain of every update ever made.</p>"),
        dict(type="mcq", prompt="<p>Why measure performance only on Release builds?</p>",
             options=["Debug builds use different GPU kernels",
                      "Debug builds compile MLX's C++ core without optimization, so CPU-side overhead inflates every timing",
                      "Release builds use the Neural Engine",
                      "Debug builds disable lazy evaluation"], answer=1,
             explain="<p>The Metal kernels are the same; the C++ code that builds and dispatches them is much slower unoptimized. Debug timings mostly measure that overhead.</p>"),
    ],
))

# ------------------------------------------------------------------ 4
LESSONS.append(dict(
    part="Part I · Foundations",
    title="Modules, parameters and fast kernels",
    blurb="Neural network code in MLX is a tree of modules whose parameter names match the checkpoint. Learn that tree, quantized layers, compile, the fused fast kernels, and how to write your own Metal kernel.",
    viz=False,
    goals=[
        "Write an MLXNN module whose parameter names match a checkpoint",
        "Load weights with update(parameters:verify:) and know what verify catches",
        "Describe what a QuantizedLinear stores",
        "Use compile to fuse elementwise work",
        "Use the fast RMSNorm, RoPE and attention kernels, and write a custom Metal kernel",
    ],
    recap="A Module's parameters form a tree whose dotted paths are the checkpoint's tensor names; @ModuleInfo(key:) sets each name. Loading weights is a dictionary update, and verify: [.all] turns naming mistakes into immediate errors. Quantized layers replace a weight with packed integers plus per-group scales and biases. compile fuses elementwise operations, and MLXFast provides fused kernels for the transformer's hot paths.",
    sections=[
        dict(title="Modules are named trees", body="""
<p>A model is a tree of <code>Module</code> objects. Each one owns parameters (arrays) and child modules. The key fact for an inference engine is that <strong>the dotted path of every parameter is its name in the checkpoint</strong>.</p>
""" + source("Sources/mlx-basics/main.swift", "final class TinyMLP") + """
<p><code>@ModuleInfo(key: "up_proj")</code> says: this child appears as <code>up_proj</code> in the parameter tree. The Swift property can have any name you like (<code>up</code>), but the key must match the checkpoint exactly. Qwen's real MLP is the same shape with three projections, and its parameters are called <code>model.layers.3.mlp.up_proj.weight</code> because the module tree nests: model → layers → index 3 → mlp → up_proj → weight.</p>
<p>Implement <code>callAsFunction</code> and the module can be called like a function. Conforming to <code>UnaryLayer</code> (one array in, one array out) lets you store different implementations behind one property, which Lesson 16 uses to swap a dense MLP for a mixture-of-experts layer.</p>
"""),
        dict(title="Loading weights", body="""
""" + source("Sources/mlx-basics/main.swift", "func modulesAndParameters") + """
<p><code>parameters().flattened()</code> lists the tree as <code>(path, array)</code> pairs. Loading is the reverse: build a flat <code>[String: MLXArray]</code> dictionary, turn it into a tree with <code>ModuleParameters.unflattened</code>, and <code>update</code> the module.</p>
<p>Always pass <code>verify: [.all]</code>. It throws if the dictionary has a key the model lacks, if the model has a parameter the dictionary lacks, or if a shape does not match. Without it, a typo in a key silently leaves that layer with its initial values, and the model produces fluent-looking garbage that is very hard to debug. With it, the first run tells you exactly which name is wrong.</p>
"""),
        dict(title="Quantized layers", body="""
""" + source("Sources/mlx-basics/main.swift", "func quantizedLinear") + """
<p>A <code>QuantizedLinear</code> stores the same matrix in three arrays:</p>
<ul>
<li><code>weight</code>: 4-bit integers packed eight to a <code>UInt32</code>, so a 512×256 matrix becomes 512×32 words;</li>
<li><code>scales</code> and <code>biases</code>: one of each per group of 64 consecutive weights in a row, in bfloat16.</li>
</ul>
<p>Each real weight is reconstructed as <code>scale × q + bias</code>, with <code>q</code> an integer from 0 to 15. The fast kernels never rebuild the full matrix: they unpack, scale and multiply in registers as they stream the packed weights from memory. That is the whole point, because Lesson 2 showed that the bytes read are the cost. Lesson 5 covers the format in detail.</p>
<p>The module-level <code>quantize(model:filter:)</code> function walks a model and replaces every <code>Linear</code> and <code>Embedding</code> the filter accepts with its quantized version. Our loaders use it to match a pre-quantized checkpoint, or to quantize a full-precision one while loading.</p>
"""),
        dict(title="compile: fusing elementwise work", body="""
""" + source("Sources/mlx-basics/main.swift", "func compiledFunctions") + """
<p>Each MLX operation normally becomes its own GPU kernel, which reads its inputs from memory and writes its output back. For elementwise chains like <code>silu(gate) * up</code>, that means several full passes over the data. <code>compile</code> traces the function once and emits a single fused kernel, which reads each input once and writes once. <code>shapeless: true</code> lets one compiled function serve every input shape, which matters because sequence lengths change all the time.</p>
<p>The model code in this course compiles exactly this <code>swiglu</code> function, matching the Python reference. Compilation is a performance tool here: the fused and unfused results are identical in this example.</p>
"""),
        dict(title="The fast kernels", body="""
<p>Three operations dominate a transformer layer apart from the matrix multiplies, and MLX ships hand-written Metal kernels for each:</p>
""" + source("Sources/mlx-basics/main.swift", "func fastKernels") + """
<ul>
<li><code>MLXFast.rmsNorm</code> normalizes each vector by its root-mean-square and scales it by a learned weight, in one pass.</li>
<li><code>MLXFast.RoPE</code> rotates pairs of dimensions by angles that depend on the token's position. <code>offset</code> is the position of the first token in the array, which is how a cached decode step knows it is at position 517 and not 0.</li>
<li><code>MLXFast.scaledDotProductAttention</code> computes <code>softmax(QKᵀ·scale + mask)·V</code> without materializing the full score matrix. Its <code>mask</code> argument takes <code>.causal</code> (each position attends only to itself and earlier ones), <code>.none</code>, or an explicit array. It also handles grouped-query attention, where several query heads share one key/value head, by itself.</li>
</ul>
"""),
        dict(title="Your own Metal kernel", body="""
<p>When no built-in operation does what you need efficiently, <code>MLXFast.metalKernel</code> compiles a Metal function from a string at run time:</p>
""" + source("Sources/mlx-basics/main.swift", "func customKernel") + """
<p>You write only the body. MLX generates the function signature from the input and output names, passes each input as a device pointer, and lets you set template parameters (types and integer constants) per call. <code>grid</code> is the total number of threads and <code>threadGroup</code> how many run together and can share fast memory.</p>
<p>This looks like a curiosity now. In Lesson 17 it is essential: Qwen3.5's linear-attention recurrence written with ordinary operations launches several kernels per token, and a custom kernel that keeps the state in registers makes prefill about 3× faster.</p>
"""),
    ],
    exercises=[
        dict(type="fill", prompt="<p>A module has <code>@ModuleInfo(key: \"self_attn\") var attention: Attention</code>, and Attention has <code>@ModuleInfo(key: \"q_proj\") var q: Linear</code>. The parent is stored in a model under <code>layers.0</code>. What is the full name of the query weight?</p>",
             answer=["layers.0.self_attn.q_proj.weight"], placeholder="dotted path",
             explain="<p>Keys nest: layers → 0 → self_attn → q_proj → weight. Swift property names (<code>attention</code>, <code>q</code>) do not appear.</p>"),
        dict(type="mcq", prompt="<p>Your loader misspells a key, <code>mlp.gate_prj.weight</code>. What does <code>update(parameters:verify: [.all])</code> do?</p>",
             options=["Loads everything else and ignores the typo",
                      "Throws, naming the unexpected key and the missing parameter",
                      "Guesses the closest name",
                      "Crashes at the first forward pass"], answer=1,
             explain="<p>verify .all rejects extra keys, missing parameters and shape mismatches, so naming errors surface at load time instead of as garbage output.</p>"),
        dict(type="numeric", prompt="<p>A 4096×4096 weight is quantized to 4 bits with group size 64 and bfloat16 scales and biases. How many megabytes (10<sup>6</sup> bytes) do the scales and biases take together? Two decimals.</p>",
             answer=1.05, tolerance=0.006, placeholder="MB",
             explain="<p>Each row has 4096 / 64 = 64 groups, so 4096 × 64 = 262,144 groups. Each group stores one scale and one bias at 2 bytes each: 262,144 × 4 = 1,048,576 bytes ≈ 1.05 MB. The packed weights themselves take 4096 × 4096 / 2 = 8 MB.</p>"),
        dict(type="mcq", prompt="<p>What does <code>offset</code> do in <code>MLXFast.RoPE(x, ..., offset: 517)</code>?</p>",
             options=["Skips the first 517 dimensions",
                      "Treats the first token of x as position 517, so cached decoding rotates by the right angle",
                      "Adds 517 to every value",
                      "Uses only the last 517 tokens"], answer=1,
             explain="<p>RoPE angles depend on absolute position. During decode, the single new token sits after everything in the cache, so its position is the cache length.</p>"),
        dict(type="mcq", prompt="<p>Why does compiling <code>silu(gate) * up</code> make it faster?</p>",
             options=["It switches to lower precision",
                      "It fuses the operations into one kernel, so the data is read and written once instead of once per operation",
                      "It moves the work to the CPU",
                      "It caches the result between calls"], answer=1,
             explain="<p>Elementwise work is memory-bound. Fusing removes the intermediate round trips through memory.</p>"),
    ],
))

# ------------------------------------------------------------------ 5
LESSONS.append(dict(
    part="Part II · Running Qwen",
    title="Reading a checkpoint",
    blurb="A Hugging Face model is a folder of JSON and safetensors files. Learn what is in each, how weights are named, and exactly how MLX's 4-bit format stores a matrix.",
    viz=True,
    goals=[
        "Read a model's config.json and know which fields the code needs",
        "Explain the safetensors format and why it loads fast",
        "Map checkpoint tensor names to modules, including tied embeddings",
        "Compute the size and error of MLX affine group quantization",
        "Write the Qwen3 config type and weight loader",
    ],
    recap="A checkpoint folder holds config.json (architecture hyperparameters), tokenizer files, and safetensors shards: a JSON header followed by raw tensor bytes, so loading is little more than mapping the file. Tensor names are module paths. MLX's affine quantization stores each group of 64 weights as 4-bit integers plus a bfloat16 scale and bias, about 4.5 bits per weight.",
    sections=[
        dict(title="What is in the folder", body="""
<p>Download <code>mlx-community/Qwen3-0.6B-4bit</code>, the small model used through Lesson 10, and list it:</p>
""" + block('''config.json              architecture hyperparameters
model.safetensors        the weights (large models split this into shards)
model.safetensors.index.json   which tensor is in which shard
tokenizer.json           the BPE vocabulary and merge rules
tokenizer_config.json    special tokens and the chat template
vocab.json, merges.txt, added_tokens.json, special_tokens_map.json''', "text") + """
<p>Two files define the model: <code>config.json</code> and the safetensors. The tokenizer files are the subject of the next lesson.</p>
"""),
        dict(title="config.json", body="""
""" + block('''{
  "architectures": ["Qwen3ForCausalLM"],
  "model_type": "qwen3",
  "hidden_size": 1024,
  "num_hidden_layers": 28,
  "intermediate_size": 3072,
  "num_attention_heads": 16,
  "num_key_value_heads": 8,
  "head_dim": 128,
  "rms_norm_eps": 1e-06,
  "rope_theta": 1000000,
  "vocab_size": 151936,
  "tie_word_embeddings": true,
  "quantization": {"group_size": 64, "bits": 4},
  ...
}''', "text") + """
<p>Each field becomes a dimension or a constant in the model code: the width of the hidden vector, the number of layers, the MLP's inner width, how many query and key/value heads attention uses, the base frequency of the rotary position encoding, and the vocabulary size. <code>model_type</code> tells the server which implementation to use. <code>quantization</code> appears only in pre-quantized MLX checkpoints.</p>
<p>The Swift side is a <code>Codable</code> struct with only the fields the code uses. <code>convertFromSnakeCase</code> maps <code>num_hidden_layers</code> to <code>numHiddenLayers</code>, so no coding keys are needed:</p>
""" + source("Sources/Inference/Qwen3Config.swift", "public struct Qwen3Config", "    public struct Quantization", include_end=False) + """
<p>The real file also has optional mixture-of-experts fields (Lesson 16) and a <code>load(from:)</code> helper that decodes the file with that key strategy.</p>
"""),
        dict(title="safetensors", body="""
<p>A <code>.safetensors</code> file is deliberately simple:</p>
<ol>
<li>8 bytes: the length of the header, as a little-endian integer;</li>
<li>the header: JSON mapping each tensor name to its dtype, shape and byte range;</li>
<li>the raw bytes of every tensor, back to back.</li>
</ol>
""" + block('''{"model.layers.0.mlp.down_proj.weight": {"dtype": "U32", "shape": [1024, 384],
                                         "data_offsets": [0, 1572864]},
 "model.layers.0.mlp.down_proj.scales": {"dtype": "BF16", "shape": [1024, 48], ...},
 ...}''', "text") + """
<p>There is no code in the file, unlike Python pickle-based formats, so loading one cannot execute anything. And because each tensor is a contiguous byte range at a known offset, a loader can map the file into memory and hand the bytes to the GPU directly. <code>MLX.loadArrays(url:)</code> returns a <code>[String: MLXArray]</code> whose arrays are read lazily.</p>
<p>Large models are split into shards (<code>model-00001-of-00004.safetensors</code>, ...) with an index file. Our loader simply reads every <code>.safetensors</code> file in the folder and merges the dictionaries, which works for one file or fifty.</p>
"""),
        dict(title="Names and tied embeddings", body="""
<p>The tensor names are the module paths from Lesson 4. For Qwen3:</p>
<table>
<tr><th>Name</th><th>Shape (bf16 model)</th><th>What it is</th></tr>
<tr><td><code>model.embed_tokens.weight</code></td><td>[151936, 1024]</td><td>one vector per token id</td></tr>
<tr><td><code>model.layers.N.input_layernorm.weight</code></td><td>[1024]</td><td>RMSNorm before attention</td></tr>
<tr><td><code>model.layers.N.self_attn.{q,k,v,o}_proj.weight</code></td><td>[2048, 1024], [1024, 1024], ...</td><td>attention projections</td></tr>
<tr><td><code>model.layers.N.self_attn.{q,k}_norm.weight</code></td><td>[128]</td><td>per-head RMSNorm on queries and keys</td></tr>
<tr><td><code>model.layers.N.mlp.{gate,up,down}_proj.weight</code></td><td>[3072, 1024], ...</td><td>the SwiGLU MLP</td></tr>
<tr><td><code>model.norm.weight</code></td><td>[1024]</td><td>final RMSNorm</td></tr>
</table>
<p>One name is conspicuously missing: <code>lm_head.weight</code>, the output projection from a hidden vector to 151,936 logits. With <code>tie_word_embeddings: true</code> the model reuses the embedding matrix for it, read the other way round: the logit for token <em>t</em> is the dot product of the hidden vector with token <em>t</em>'s embedding. That saves 155 million parameters on this small model, a quarter of its total. In MLX, <code>Embedding.asLinear(x)</code> does exactly this multiply, quantized or not.</p>
"""),
        dict(title="Affine group quantization", body="""
<p>MLX's default quantization is <strong>affine, per group</strong>. Take a row of the weight matrix and cut it into groups of 64 consecutive values. For each group:</p>
<ol>
<li>find its minimum and maximum;</li>
<li>set <code>scale = (max − min) / 15</code> and <code>bias = min</code>, so the 16 integer levels 0..15 span the group's range;</li>
<li>store each weight as <code>q = round((w − bias) / scale)</code>, a 4-bit integer.</li>
</ol>
<p>Reconstruction is <code>w ≈ scale × q + bias</code>. The error per weight is at most half a step, <code>scale / 2</code>, so groups with a narrow range are stored precisely and one outlier only hurts its own group of 64. Try it in the diagram: drag the outlier and watch the step size, and the error of every other weight in the group, grow.</p>
<p><strong>Storage.</strong> Each weight costs 4 bits. Each group also stores a bfloat16 scale and bias, 32 bits shared by 64 weights, which is 0.5 bits per weight. So "4-bit" really means <strong>4.5 bits per weight</strong>, and 8-bit means 8.5. In the file you see this as three tensors per layer: <code>weight</code> as <code>U32</code> with 8 values packed per word, so its last dimension is <code>in / 8</code>; and <code>scales</code> and <code>biases</code> with last dimension <code>in / 64</code>.</p>
""", figure=fig("viz-quant", "One group of 64 weights at 4 bits",
                "Rings are the original weights, blue dots their 4-bit reconstructions, horizontal lines the 16 levels. Drag the slider to move the orange outlier and watch the levels spread apart.")),
        dict(title="The loader", body="""
""" + source("Sources/Inference/Loader.swift", "public func loadQwen3") + """
<p>Four steps, and the order matters:</p>
<ol>
<li><strong>Read</strong> every shard into one flat dictionary.</li>
<li><strong>Clean up</strong> names: drop <code>lm_head.weight</code> for tied models, and stack per-expert tensors for mixture-of-experts models (Lesson 16).</li>
<li><strong>Quantize the module tree first</strong>. A fresh model has float <code>Linear</code> layers expecting a <code>[1024, 1024]</code> weight, but the file holds a packed <code>[1024, 128]</code> integer weight plus scales and biases. <code>quantize</code> swaps each layer whose name has a <code>.scales</code> entry in the file for a <code>QuantizedLinear</code>, so the shapes line up.</li>
<li><strong>Update with verification</strong>, then <code>eval</code> once so the weights are materialized before the first request instead of during it.</li>
</ol>
<p>The Qwen3.5 loader in Lesson 17 adds one more trick: it loads an original bfloat16 checkpoint and quantizes it itself, which is how it keeps the MTP head that pre-converted community checkpoints strip out.</p>
"""),
    ],
    exercises=[
        dict(type="numeric", prompt="<p>MLX 8-bit quantization with group size 64 and bfloat16 scales and biases. How many bits does each weight cost on average?</p>",
             answer=8.5, tolerance=0.01, placeholder="bits",
             explain="<p>8 bits for the value, plus 32 bits of scale and bias shared by 64 weights = 0.5. Total 8.5.</p>"),
        dict(type="numeric", prompt="<p>A 4-bit MLX checkpoint has <code>model.embed_tokens.weight</code> with shape [151936, 128] and dtype U32. What is the model's hidden size?</p>",
             answer=1024, tolerance=0, placeholder="hidden size",
             explain="<p>Each UInt32 packs eight 4-bit values, so 128 words hold 1024 weights per row.</p>"),
        dict(type="mcq", prompt="<p>A Qwen3 checkpoint has no <code>lm_head.weight</code>. Where do the logits come from?</p>",
             options=["A randomly initialized head",
                      "The embedding matrix, used as the output projection (tied embeddings)",
                      "The last layer's MLP",
                      "The tokenizer"], answer=1,
             explain="<p>With tie_word_embeddings the same matrix maps ids to vectors on the way in and vectors to logits on the way out. Embedding.asLinear does the second direction.</p>"),
        dict(type="mcq", prompt="<p>Why must the loader call <code>quantize(model:)</code> <em>before</em> <code>update(parameters:)</code> for a pre-quantized checkpoint?</p>",
             options=["Quantizing afterwards would be slower",
                      "The fresh model's float Linear layers expect full-size weights; the file holds packed weights plus scales and biases, so the layers must be swapped first for names and shapes to match",
                      "update only accepts quantized modules",
                      "It does not matter"], answer=1,
             explain="<p>QuantizedLinear has weight, scales and biases parameters of different shapes. Swapping first makes the module tree match the file exactly, so verify .all passes.</p>"),
        dict(type="numeric", prompt="<p>A group's weights range from −0.30 to 0.45. With 4-bit affine quantization, what is the largest possible rounding error for a weight in this group? (Give it to three decimals.)</p>",
             answer=0.025, tolerance=0.0006, placeholder="error",
             explain="<p>scale = (0.45 − (−0.30)) / 15 = 0.05. Rounding to the nearest level is off by at most half a step: 0.025.</p>"),
    ],
))
