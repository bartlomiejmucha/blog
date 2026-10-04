window.COURSE = {
  "lessons": [
    {
      "id": "l01",
      "num": 1,
      "title": "What an inference server does",
      "file": "01-what-an-inference-server-does.html",
      "part": "Part I \u00b7 Foundations",
      "blurb": "Before writing code, see the whole machine: what happens between an HTTP request arriving and the last token leaving, and which part of the code owns each step.",
      "exercises": 4
    },
    {
      "id": "l02",
      "num": 2,
      "title": "Apple Silicon and the memory-bandwidth bound",
      "file": "02-apple-silicon-and-the-memory-bandwidth-bound.html",
      "part": "Part I \u00b7 Foundations",
      "blurb": "Generating one token means reading every weight of the model once. On a Mac that makes memory bandwidth, not compute, the speed limit, and it explains almost every design choice in this course.",
      "exercises": 4
    },
    {
      "id": "l03",
      "num": 3,
      "title": "MLX Swift basics",
      "file": "03-mlx-swift-basics.html",
      "part": "Part I \u00b7 Foundations",
      "blurb": "Set up the package, then learn the four ideas you will use on every page that follows: arrays and shapes, dtypes, lazy evaluation, and asynchronous evaluation.",
      "exercises": 5
    },
    {
      "id": "l04",
      "num": 4,
      "title": "Modules, parameters and fast kernels",
      "file": "04-modules-parameters-and-fast-kernels.html",
      "part": "Part I \u00b7 Foundations",
      "blurb": "Neural network code in MLX is a tree of modules whose parameter names match the checkpoint. Learn that tree, quantized layers, compile, the fused fast kernels, and how to write your own Metal kernel.",
      "exercises": 5
    },
    {
      "id": "l05",
      "num": 5,
      "title": "Reading a checkpoint",
      "file": "05-reading-a-checkpoint.html",
      "part": "Part II \u00b7 Running Qwen",
      "blurb": "A Hugging Face model is a folder of JSON and safetensors files. Learn what is in each, how weights are named, and exactly how MLX's 4-bit format stores a matrix.",
      "exercises": 5
    },
    {
      "id": "l06",
      "num": 6,
      "title": "Tokenizer and chat template",
      "file": "06-tokenizer-and-chat-template.html",
      "part": "Part II \u00b7 Running Qwen",
      "blurb": "The model only sees integers. Turn chat messages into exactly the token sequence Qwen was trained on, and turn generated tokens back into text that can be streamed safely.",
      "exercises": 5
    },
    {
      "id": "l07",
      "num": 7,
      "title": "Implementing Qwen3",
      "file": "07-implementing-qwen3.html",
      "part": "Part II \u00b7 Running Qwen",
      "blurb": "Write the whole Qwen3 decoder in about 150 lines: grouped-query attention with QK-norm and rotary positions, a SwiGLU MLP, pre-norm residual blocks, and a tied output head.",
      "exercises": 5
    },
    {
      "id": "l08",
      "num": 8,
      "title": "Loading weights and proving parity",
      "file": "08-loading-weights-and-proving-parity.html",
      "part": "Part II \u00b7 Running Qwen",
      "blurb": "A model that loads and produces fluent text can still be wrong. Prove yours matches the reference, learn what agreement in bfloat16 actually looks like, and how to find the first layer that disagrees.",
      "exercises": 4
    },
    {
      "id": "l09",
      "num": 9,
      "title": "The generation loop and the KV cache",
      "file": "09-the-generation-loop-and-the-kv-cache.html",
      "part": "Part II \u00b7 Running Qwen",
      "blurb": "Turn a model into a token stream: prefill the prompt in chunks, keep every past key and value in a cache that grows in steps, and overlap CPU and GPU work so the GPU never waits.",
      "exercises": 5
    },
    {
      "id": "l10",
      "num": 10,
      "title": "Sampling",
      "file": "10-sampling.html",
      "part": "Part II \u00b7 Running Qwen",
      "blurb": "Logits are scores, not choices. Implement greedy decoding, temperature, top-k, top-p and min-p on the GPU, with reproducible seeds, and learn what each knob does to the distribution.",
      "exercises": 5
    },
    {
      "id": "l11",
      "num": 11,
      "title": "An OpenAI-compatible API with Hummingbird",
      "file": "11-an-openai-compatible-api-with-hummingbird.html",
      "part": "Part III \u00b7 The server",
      "blurb": "Put an HTTP front on the engine that speaks the Chat Completions wire format, so every existing OpenAI client and SDK can use your server unchanged.",
      "exercises": 4
    },
    {
      "id": "l12",
      "num": 12,
      "title": "Streaming and cancellation",
      "file": "12-streaming-and-cancellation.html",
      "part": "Part III \u00b7 The server",
      "blurb": "Send each piece of text the moment it exists with server-sent events, and stop generating the instant a client goes away so the GPU is never wasted on nobody.",
      "exercises": 4
    },
    {
      "id": "l13",
      "num": 13,
      "title": "One GPU, many clients",
      "file": "13-one-gpu-many-clients.html",
      "part": "Part III \u00b7 The server",
      "blurb": "Many HTTP requests arrive at once, but the model must run on one thread at a time. Build the serial engine: a dedicated worker thread, a locked inbox, backpressure, and a clear rule for which objects each thread may touch.",
      "exercises": 4
    },
    {
      "id": "l14",
      "num": 14,
      "title": "Prompt caching",
      "file": "14-prompt-caching.html",
      "part": "Part III \u00b7 The server",
      "blurb": "The second turn of a chat repeats the whole first turn. Keep the caches of recent requests and skip prefilling what the server has already seen, and learn why where you take the snapshot matters as much as how you match it.",
      "exercises": 4
    },
    {
      "id": "l15",
      "num": 15,
      "title": "Continuous batching",
      "file": "15-continuous-batching.html",
      "part": "Part III \u00b7 The server",
      "blurb": "Serve several sequences in each decode step so the weights are read once for all of them. Build a batching engine without padding, then measure how much it really helps on an M1, and why the answer depends on the matmul kernel.",
      "exercises": 5
    },
    {
      "id": "l16",
      "num": 16,
      "title": "Mixture of experts",
      "file": "16-mixture-of-experts.html",
      "part": "Part IV \u00b7 Advanced",
      "blurb": "Replace the MLP with many expert MLPs and a router that picks a few per token. Implement routing, gathered matrix multiplies and expert stacking, and verify them against tiny random checkpoints you can run on any Mac.",
      "exercises": 5
    },
    {
      "id": "l17",
      "num": 17,
      "title": "Qwen3.5's hybrid architecture",
      "file": "17-qwen3-5-s-hybrid-architecture.html",
      "part": "Part IV \u00b7 Advanced",
      "blurb": "Three of every four Qwen3.5 layers drop softmax attention for Gated DeltaNet, a linear attention whose memory is a fixed-size matrix. Implement it with plain ops, then as a custom Metal kernel, and implement the gated full-attention layers in between.",
      "exercises": 5
    },
    {
      "id": "l18",
      "num": 18,
      "title": "Speculative decoding",
      "file": "18-speculative-decoding.html",
      "part": "Part IV \u00b7 Advanced",
      "blurb": "Guess several tokens cheaply, then check them all with one pass of the real model. Learn the acceptance rule that keeps output exactly as good as normal decoding, and the cost model that says when it actually speeds things up.",
      "exercises": 5
    },
    {
      "id": "l19",
      "num": 19,
      "title": "MTP: Qwen3.5's built-in drafter",
      "file": "19-mtp-qwen3-5-s-built-in-drafter.html",
      "part": "Part IV \u00b7 Advanced",
      "blurb": "Every Qwen3.5 checkpoint ships a one-layer head trained to predict two tokens ahead. Wire it up as the drafter, roll back linear-attention state on rejection, remove the hidden GPU waits, and measure where it pays off.",
      "exercises": 5
    },
    {
      "id": "l20",
      "num": 20,
      "title": "Performance engineering",
      "file": "20-performance-engineering.html",
      "part": "Part IV \u00b7 Advanced",
      "blurb": "Measure before optimizing, and measure correctly. Collect every performance lesson from building this server into one method: what to time, how to keep the numbers honest, and which changes actually moved them.",
      "exercises": 4
    },
    {
      "id": "l21",
      "num": 21,
      "title": "Production: tools, metrics and deployment",
      "file": "21-production-tools-metrics-and-deployment.html",
      "part": "Part IV \u00b7 Advanced",
      "blurb": "Finish the server: tool calling in both Qwen formats, streamed correctly; Prometheus metrics; running it as a service; and an honest list of what a production deployment would still need.",
      "exercises": 4
    }
  ]
};
