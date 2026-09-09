# -*- coding: utf-8 -*-
"""Part III/IV — lessons 11-14."""
from content_part1 import fig

LESSONS = []

# ------------------------------------------------------------------ 11
LESSONS.append(dict(
    part="Part III · Generation",
    title="Context windows and the KV cache",
    blurb="Why the first token of a response is slow and the rest are fast, why long prompts cost memory rather than just time, and what actually fills up when you 'run out of context'.",
    viz=True,
    goals=[
        "Explain what the KV cache stores and why it is possible",
        "Distinguish the prefill and decode phases and their bottlenecks",
        "Compute KV cache size for a given model and sequence length",
        "Explain why decoding is memory-bandwidth bound, and what that implies",
    ],
    recap="Because of causal masking, past tokens' keys and values never change. Cache them and each new token costs one forward pass over a single position. Prefill is compute-bound and parallel; decode is memory-bandwidth-bound and sequential. The cache is what makes long context expensive in memory.",
    sections=[
        dict(title="The redundancy", body="""
<p>Naive generation is absurdly wasteful. To produce token 101 you run the model over tokens 1–100. To produce token 102 you run it over tokens 1–101 — recomputing everything you just computed.</p>
<p>The causal mask makes the fix possible. Position 50 can only attend to positions ≤ 50, so <strong>adding token 101 cannot change anything about position 50</strong>. Its key and value vectors are final the moment they are computed.</p>
<p>So cache them. For every layer and every head, store the K and V vectors of every token processed so far. Generating a new token then requires computing Q, K, V for <em>one</em> position, attending against the whole cache, and appending the new K and V.</p>
<p>Note that only K and V are cached, never Q. A query is used once, at the step that created it, and then is of no further use.</p>
""", figure=fig("viz-kvcache", "Cache growth",
                "Generate tokens with the cache on and off, and compare the work done at each step.")),
        dict(title="Two phases with different physics", body="""
<p>This split is the single most useful thing to understand about LLM serving.</p>
<p><strong>Prefill</strong> — processing your prompt. All prompt tokens go through the model together in one parallel pass, filling the cache. This is a big matrix–matrix multiplication: the GPU is doing heavy arithmetic and is <strong>compute-bound</strong>. Cost scales with prompt length (plus a quadratic term from attention). It determines your time-to-first-token.</p>
<p><strong>Decode</strong> — generating the response, one token at a time. Each step is a matrix–<em>vector</em> multiplication: to produce a single token, the GPU must read <em>every weight in the model</em> from memory and use each one for very little arithmetic. The chip is starved for data, not for compute. Decode is <strong>memory-bandwidth-bound</strong>.</p>
<p>Consequences that surprise people:</p>
<ul>
  <li>Decoding one token at a time uses a tiny fraction of a GPU's arithmetic capability. The hardware is mostly idle, waiting on memory.</li>
  <li>The weights are not the only thing read each step — the attention at every layer reads the whole KV cache too. That is why decoding slows down as a conversation grows: at 8k tokens the cache in the example below is 21.5 GB against 140 GB of weights, but at 128k it is 344 GB and has become the larger of the two reads.</li>
  <li><strong>Batching is nearly free during decode.</strong> The weights are read once and shared across all sequences in the batch, so serving 32 users costs barely more time per step than serving one. This is why batch throughput is the metric providers optimise.</li>
  <li>Making weights smaller — quantization, Lesson 17 — speeds up decode almost linearly, because the bottleneck is bytes moved, not maths done.</li>
  <li>Output tokens are typically priced higher than input tokens, and this is why: input is processed in parallel, output is strictly sequential.</li>
</ul>
"""),
        dict(title="How big is the cache?", body="""
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-xs leading-6 text-ink-100">cache_bytes = 2 × n_layers × n_kv_heads × d_head × seq_len × bytes_per_value</p>
<p>The 2 is for K and V. Worked example — a 70B-class model: 80 layers, 64 heads with <code>d_head</code> 128, fp16 (2 bytes), 8k tokens:</p>
<p class="font-mono text-xs text-ink-300">2 × 80 × 64 × 128 × 8192 × 2 ≈ 21.5 GB</p>
<p>That is on top of 140 GB of weights, for a <em>single</em> sequence. Now serve 20 users concurrently and the cache alone is 430 GB. This is the reason grouped-query attention exists: with 8 KV groups instead of 64 heads, that 21.5 GB becomes 2.7 GB.</p>
<p>Other techniques in production use: <strong>paged attention</strong> (vLLM), which stores the cache in fixed-size blocks like operating-system virtual memory to eliminate fragmentation; <strong>prefix caching</strong>, which reuses the cache for a shared system prompt across requests; and cache quantization to 8 or 4 bits.</p>
""", figure=fig("viz-cachesize", "KV cache calculator",
                "Set the model shape and sequence length; compare full multi-head against GQA.")),
        dict(title="What 'running out of context' means", body="""
<p>The context window is the maximum number of tokens in a single forward pass — prompt plus generated output together. Hitting it means one of three things happened:</p>
<ul>
  <li>The position encoding runs past what the model was trained on (Lesson 7).</li>
  <li>The KV cache no longer fits in memory.</li>
  <li>The provider set a limit for cost reasons.</li>
</ul>
<p>Practical strategies when you exceed it: sliding-window attention (each token only attends to the last N, keeping cost linear but genuinely losing distant information); summarising older conversation turns; retrieval instead of stuffing (Lesson 16); or the <strong>attention sink</strong> trick, keeping the first few tokens permanently in the cache alongside a sliding window, which preserves quality far better than a naive window.</p>
<div class="note"><p class="text-sm"><strong>Longer context is not free accuracy.</strong> Beyond cost, models attend less reliably to the middle of very long inputs. If a document is 100k tokens and only 2k are relevant, retrieving those 2k usually beats sending everything — cheaper and often more accurate.</p></div>
"""),
    ],
    exercises=[
        dict(type="mcq",
             prompt="<p>Why is it valid to cache the key and value vectors of past tokens?</p>",
             options=["Because attention weights are always the same",
                      "Because causal masking means a past position never attends to later tokens, so its K and V never change",
                      "Because the embedding table is static",
                      "Because the FFN does not mix positions"],
             answer="1",
             explain="Nothing that happens later can influence an earlier position's representation in a causal model. That makes its K and V final and safe to reuse forever."),
        dict(type="mcq",
             prompt="<p>Which is the bottleneck during the decode phase of generation?</p>",
             options=["GPU arithmetic throughput",
                      "Memory bandwidth — reading all the model weights for each single token",
                      "The tokenizer",
                      "Network latency to the client"],
             answer="1",
             explain="One token requires reading every weight and doing almost no arithmetic per byte read. This is why quantization gives near-linear decode speedups and why batching is close to free."),
        dict(type="numeric",
             prompt="<p>A model has 32 layers, 8 KV heads, <code>d_head</code> = 128, and stores the cache in fp16 (2 bytes). How many megabytes does the cache take for 1024 tokens? (1 MB = 1,048,576 bytes; answer to the nearest 10 MB.)</p>",
             answer="128", tolerance=15,
             placeholder="megabytes",
             explain="2 × 32 × 8 × 128 × 1024 × 2 = 134,217,728 bytes = exactly 128 MB. Scale to 32k tokens and it is 4 GB — per sequence."),
        dict(type="multi",
             prompt="<p>Which are true of the prefill phase? Select all.</p>",
             options=["All prompt tokens are processed in parallel in one pass",
                      "It is generally compute-bound rather than memory-bandwidth-bound",
                      "It determines time-to-first-token",
                      "It happens once per generated token"],
             answer=[0, 1, 2],
             explain="Prefill runs once for the prompt. The per-token work afterwards is decode, which has completely different performance characteristics."),
        dict(type="mcq",
             prompt="<p>You must serve many concurrent users of a long-context model and are running out of GPU memory. Which change targets the KV cache most directly?</p>",
             options=["Lowering the temperature",
                      "Switching from multi-head to grouped-query attention",
                      "Adding more transformer layers",
                      "Increasing the vocabulary size"],
             answer="1",
             explain="GQA cuts the number of stored K/V heads by the grouping factor, shrinking the cache proportionally. Paged attention and cache quantization are the other standard levers."),
    ],
))

# ------------------------------------------------------------------ 12
LESSONS.append(dict(
    part="Part IV · Training",
    title="Pretraining: how the weights get their values",
    blurb="Billions of parameters start as random noise. Gradient descent on next-token prediction, repeated trillions of times, turns them into a language model.",
    viz=True,
    goals=[
        "Write down the cross-entropy loss and interpret its value",
        "Explain backpropagation and gradient descent at the right level of detail",
        "Describe what an optimizer, learning rate schedule and batch actually do",
        "Explain what pretraining data looks like and why filtering matters",
    ],
    recap="Loss is the negative log probability the model assigned to the token that actually came next. Backpropagation computes how each weight affected that loss; the optimizer nudges every weight downhill. Repeat over trillions of tokens with a warmup-then-decay learning rate.",
    sections=[
        dict(title="Measuring wrongness", body="""
<p>Training needs a single number to minimise. For next-token prediction it is <strong>cross-entropy loss</strong>:</p>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-sm text-ink-100">loss = −log P(actual next token)</p>
<p>That is the whole thing. If the model gave the correct token probability 0.9, the loss is 0.105. If it gave it 0.1, the loss is 2.3. If it gave it 0.001, the loss is 6.9. The penalty grows sharply as the assigned probability approaches zero, which is exactly the incentive you want: <strong>being confidently wrong is punished far more than being uncertain</strong>.</p>
<p>Average this over every position in the batch and you have a number to descend.</p>
<p><strong>Perplexity</strong> is <code>exp(loss)</code>, and it has a nice reading: "the model is as confused as if it were choosing uniformly among this many options". Loss 2.3 means perplexity 10 — effectively a 10-way guess at each token. Good models on English land around loss 1.8–2.2.</p>
""", figure=fig("viz-loss", "Loss versus assigned probability",
                "Drag the probability the model assigned to the correct token and watch the loss curve.")),
        dict(title="Gradient descent", body="""
<p>You have a loss and billions of knobs. Which way do you turn each one?</p>
<p>The <strong>gradient</strong> answers this: for each weight, it is the partial derivative of the loss with respect to that weight — how much the loss would change if you nudged it up slightly. Step every weight a little in the opposite direction and the loss goes down.</p>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-sm text-ink-100">w ← w − learning_rate × ∂loss/∂w</p>
<p><strong>Backpropagation</strong> is how you get all those derivatives efficiently. Run the forward pass, keeping the intermediate activations. Then walk backwards through the computation graph, applying the chain rule layer by layer. The cost is roughly twice the forward pass, regardless of how many parameters there are — which is the fact that makes training large networks feasible at all.</p>
<p>Nobody uses plain gradient descent. <strong>Adam / AdamW</strong> is the standard: it keeps a running average of each weight's gradient (momentum) and of its squared gradient (scale), giving every parameter its own effective step size. The cost is memory — two extra numbers per parameter, which is why training a 7B model needs far more than 7B × 2 bytes of GPU memory.</p>
""", figure=fig("viz-descent", "Descending a loss surface",
                "Set the learning rate and watch the path. Too small crawls; too large diverges.")),
        dict(title="The mechanics of a training run", body="""
<ul>
  <li><strong>Batching.</strong> Gradients from a single sequence are noisy, so you average over many. Large models use batches of millions of tokens, assembled across thousands of GPUs.</li>
  <li><strong>Learning rate schedule.</strong> Almost universally: linear <em>warmup</em> over the first few thousand steps (large steps on random weights destabilise training), then <em>cosine decay</em> toward near zero. The decay matters — models improve substantially in the final phase as the steps get small.</li>
  <li><strong>Gradient clipping.</strong> Cap the gradient norm to survive occasional bad batches that would otherwise blow the weights apart.</li>
  <li><strong>Mixed precision.</strong> Compute in bf16 for speed, keep a master copy of the weights in fp32 for numerical stability.</li>
  <li><strong>Checkpointing.</strong> Runs last weeks to months across thousands of GPUs; hardware fails routinely, so state is saved constantly and runs resume from the last checkpoint.</li>
</ul>
<p>One pass over the data is called an epoch, but frontier pretraining typically does roughly one epoch over an enormous corpus rather than many epochs over a small one — repeated data yields diminishing returns and eventually memorisation.</p>
"""),
        dict(title="The data", body="""
<p>Pretraining corpora are on the order of trillions of tokens: filtered web crawl (the bulk), books, code repositories, Wikipedia, academic papers, curated Q&amp;A.</p>
<p>Filtering is not a footnote — it is one of the highest-leverage parts of the whole process. Standard steps include quality classification (does this read like a reference document?), deduplication (near-duplicates cause memorisation and waste compute), removing machine-generated spam, language identification, toxicity and PII filtering, and <strong>decontamination</strong>: removing text that overlaps evaluation benchmarks, without which your reported scores measure memorisation rather than ability.</p>
<p>Data <em>mixture</em> matters too, and in non-obvious ways. Including a substantial fraction of code improves performance on reasoning tasks that have nothing to do with programming — a well-replicated result usually explained by code's strict, explicit logical structure.</p>
<p>Cost, for scale: a frontier pretraining run is thousands of GPUs for months, tens of millions of dollars, and a single unrecoverable failure can waste weeks. This is why pretraining happens rarely and fine-tuning happens constantly.</p>
"""),
    ],
    exercises=[
        dict(type="numeric",
             prompt="<p>The model assigned probability 0.5 to the token that actually came next. What is the cross-entropy loss for that position? Two decimal places.</p>",
             answer="0.69", tolerance=0.02,
             placeholder="a number",
             explain="−log(0.5) = 0.693. As a reference: probability 1.0 gives loss 0, and the loss grows without bound as the assigned probability approaches 0."),
        dict(type="numeric",
             prompt="<p>A model reports an average loss of 2.3. What is its perplexity, to the nearest whole number?</p>",
             answer="10", tolerance=0.6,
             placeholder="a number",
             explain="exp(2.3) ≈ 9.97, so about 10 — as uncertain as picking uniformly among 10 tokens at each step."),
        dict(type="mcq",
             prompt="<p>What does backpropagation compute?</p>",
             options=["The next-token probabilities",
                      "The derivative of the loss with respect to every parameter, by applying the chain rule backwards through the network",
                      "The optimal learning rate",
                      "The attention weights"],
             answer="1",
             explain="It is the efficient algorithm for getting all the gradients in roughly one backward pass — about twice the cost of the forward pass, no matter how many parameters exist."),
        dict(type="mcq",
             prompt="<p>Why do training runs start with a learning rate warmup?</p>",
             options=["To fill the KV cache",
                      "Because large steps on freshly randomised weights cause instability and divergence",
                      "Because the tokenizer needs time to adapt",
                      "To reduce memory usage early on"],
             answer="1",
             explain="Early gradients on random weights are large and unreliable. Warming up from near zero lets the model settle before taking full-size steps."),
        dict(type="multi",
             prompt="<p>Which data-preparation steps genuinely matter for pretraining quality? Select all.</p>",
             options=["Deduplicating near-identical documents",
                      "Removing text that overlaps evaluation benchmarks",
                      "Sorting the corpus alphabetically",
                      "Including a meaningful fraction of source code"],
             answer=[0, 1, 3],
             explain="Ordering by anything semantic is if anything harmful — batches should be diverse. Dedup, decontamination, and the code fraction are all well-supported quality levers."),
        dict(type="mcq",
             prompt="<p>Why does the AdamW optimizer increase memory requirements so much compared to plain SGD?</p>",
             options=["It stores the full training dataset in memory",
                      "It keeps two additional running statistics per parameter",
                      "It requires a larger batch size",
                      "It duplicates the attention cache"],
             answer="1",
             explain="Momentum plus a second-moment estimate means roughly three times the parameter memory, before you count gradients, activations and an fp32 master copy."),
    ],
))

# ------------------------------------------------------------------ 13
LESSONS.append(dict(
    part="Part IV · Training",
    title="Scaling laws: why bigger worked",
    blurb="Loss falls as a predictable power law in parameters, data and compute. That predictability is what justified spending hundreds of millions of dollars on a single training run.",
    viz=True,
    goals=[
        "State what a scaling law claims and what it does not",
        "Explain the Chinchilla result and its practical consequence",
        "Compute training compute with the 6ND rule",
        "Explain compute-optimal versus inference-optimal training",
    ],
    recap="Loss follows a power law in model size, dataset size and compute, giving straight lines on log-log axes. Chinchilla showed early models were far too large for their data; the compute-optimal ratio is roughly 20 tokens per parameter. Serving costs push production models past that, deliberately.",
    sections=[
        dict(title="What a scaling law is", body="""
<p>In 2020, OpenAI reported something unusual: language model loss falls as a <strong>power law</strong> in each of model size <code>N</code>, dataset size <code>D</code>, and compute <code>C</code>. On log-log axes, the relationship is a straight line, across many orders of magnitude.</p>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-sm text-ink-100">L(N) ≈ L<sub>∞</sub> + (N<sub>c</sub> / N)<sup>α</sup></p>
<p>The practical importance is not the equation but the <strong>predictability</strong>. Train a series of small models, fit the curve, extrapolate — and you can forecast the loss of a model 1000× larger before spending the money. Without that, no organisation would commit nine figures to a single run.</p>
<p>Read the fine print, though:</p>
<ul>
  <li>The law predicts <strong>loss</strong>, not capability. The relationship between loss and whether a model can write correct SQL is far messier.</li>
  <li>Returns are strongly diminishing. Each equal step down in loss costs exponentially more compute.</li>
  <li>Power laws describe the range where they were fitted. They are not a guarantee about regions nobody has measured.</li>
</ul>
""", figure=fig("viz-scaling", "The scaling curve",
                "Move along the compute axis and see loss on both linear and log-log axes.")),
        dict(title="Chinchilla: the correction", body="""
<p>The 2020 work suggested spending most additional compute on parameters. The field did: GPT-3 was 175B parameters trained on 300B tokens.</p>
<p>In 2022, DeepMind's Chinchilla paper redid the experiments more carefully — varying model size <em>and</em> data together at fixed compute budgets — and found this was badly wrong. The result: for compute-optimal training, <strong>parameters and tokens should scale in roughly equal proportion</strong>, around 20 tokens per parameter.</p>
<p>By that standard GPT-3 was undertrained by more than an order of magnitude. Chinchilla itself, at 70B parameters trained on 1.4T tokens, outperformed the 280B-parameter Gopher trained on far less data, using the same compute.</p>
<p>The consequence was immediate and visible: the industry stopped racing on parameter count and started racing on data quantity and quality. Model sizes plateaued or fell while token counts exploded.</p>
""", figure=fig("viz-chinchilla", "Compute-optimal frontier",
                "Fix a compute budget and slide the parameter/data split to find the loss minimum.")),
        dict(title="The 6ND rule", body="""
<p>Training compute in FLOPs is well approximated by:</p>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-sm text-ink-100">C ≈ 6 × N × D</p>
<p>where <code>N</code> is parameters and <code>D</code> is training tokens. The 6 breaks down as roughly 2 FLOPs per parameter for the forward pass and 4 for the backward pass.</p>
<p>Worked example — a 7B model on 2T tokens: <code>6 × 7×10⁹ × 2×10¹² = 8.4×10²²</code> FLOPs. On 1000 H100s delivering roughly 160 teraFLOPs each after realistic utilisation losses, that is about 6,000 GPU-days, or a week of wall-clock time. The estimator below works the same arithmetic for any size you pick.</p>
<p>The corresponding inference rule is <code>2N</code> FLOPs per generated token — forward pass only, no backward pass.</p>
""", figure=fig("viz-flops", "Compute estimator",
                "Set parameters and tokens; see FLOPs, rough GPU-days, and an order-of-magnitude cost.")),
        dict(title="Why production models are not compute-optimal", body="""
<p>Chinchilla optimises one thing: loss for a fixed <em>training</em> budget. That is the wrong objective if you are going to serve the model to millions of users, because inference cost scales with parameters and gets paid over and over.</p>
<p>So the industry deliberately overtrains: take a smaller model and train it on far more than 20 tokens per parameter. Loss is slightly worse than a compute-optimal model at the same training cost, but the model is permanently cheaper and faster to serve. Llama 3 8B, trained on 15T tokens, is roughly 1,900 tokens per parameter — nearly a hundred times the Chinchilla ratio, and an entirely rational choice.</p>
<p>What is changing now:</p>
<ul>
  <li><strong>Data is becoming the binding constraint.</strong> High-quality text on the internet is finite, which drives interest in synthetic data, multimodal data and multiple epochs.</li>
  <li><strong>Mixture-of-experts</strong> breaks the tie between parameter count and inference cost, changing the shape of the trade-off (Lesson 17).</li>
  <li><strong>Inference-time compute</strong> is a new scaling axis: spending more compute per query — longer reasoning chains, sampling many candidates — buys accuracy without any change to the weights. Scaling that has its own, separate curves.</li>
</ul>
"""),
    ],
    exercises=[
        dict(type="numeric",
             prompt="<p>Using <code>C ≈ 6ND</code>, training a 3-billion-parameter model on 500 billion tokens costs 9×10<sup>x</sup> FLOPs. What is x?</p>",
             answer="21", tolerance=0,
             placeholder="the power of 10",
             explain="6 × (3×10⁹) × (5×10¹¹). The mantissas give 6×3×5 = 90 and the powers give 10²⁰, so 90×10²⁰ = 9×10²¹. x = 21."),
        dict(type="mcq",
             prompt="<p>What did the Chinchilla paper establish?</p>",
             options=["That larger models are always better regardless of data",
                      "That for a fixed compute budget, parameters and training tokens should scale together at roughly 20 tokens per parameter",
                      "That scaling laws do not hold above 100B parameters",
                      "That data quality does not matter if there is enough of it"],
             answer="1",
             explain="It showed the previous generation was drastically undertrained. The corrected ratio redirected the whole field from parameter count toward data."),
        dict(type="mcq",
             prompt="<p>Why do companies deliberately train models past the compute-optimal token ratio?</p>",
             options=["Because it produces lower training loss",
                      "Because inference cost scales with parameters and is paid on every request forever",
                      "Because scaling laws no longer apply at large sizes",
                      "Because it requires fewer GPUs"],
             answer="1",
             explain="Overtraining a smaller model trades a slightly worse loss for a permanently cheaper, faster model to serve. For a widely deployed product that is clearly the right trade."),
        dict(type="multi",
             prompt="<p>Which are accurate caveats about scaling laws? Select all.</p>",
             options=["They predict loss, which does not translate straightforwardly into specific capabilities",
                      "They guarantee that any capability will emerge given enough compute",
                      "Returns diminish: each equal loss improvement costs exponentially more compute",
                      "They were fitted over a measured range and extrapolation beyond it is an assumption"],
             answer=[0, 2, 3],
             explain="No scaling law guarantees a specific capability. It is a smooth curve about average next-token loss, and the mapping from that to task performance is empirical and uneven."),
        dict(type="numeric",
             prompt="<p>A 13B-parameter model generates a 500-token response. Using the <code>2N</code> FLOPs-per-token rule, how many teraFLOPs (10<sup>12</sup>) of arithmetic is that in total?</p>",
             answer="13", tolerance=1,
             placeholder="teraFLOPs",
             explain="2 × 13×10⁹ = 2.6×10¹⁰ FLOPs per token; × 500 tokens = 1.3×10¹³ = 13 teraFLOPs. A modern GPU does hundreds of teraFLOPs per second, so the arithmetic is trivial — which is exactly why decode is memory-bandwidth-bound, not compute-bound."),
    ],
))

# ------------------------------------------------------------------ 14
LESSONS.append(dict(
    part="Part IV · Training",
    title="Post-training: SFT, RLHF and DPO",
    blurb="A pretrained model completes text; it does not answer questions. Turning a document-completer into an assistant is a separate stage, and it is where most of the behaviour you interact with comes from.",
    viz=True,
    goals=[
        "Explain why a base model is not usable as an assistant",
        "Describe supervised fine-tuning and what data it needs",
        "Explain the RLHF pipeline including the reward model and PPO",
        "Explain how DPO removes the reward model, and what alignment tax means",
    ],
    recap="SFT teaches the format by imitating good demonstrations. RLHF trains a reward model on human preference comparisons and optimises the policy against it. DPO derives a direct loss on preference pairs, skipping the reward model entirely. Post-training changes behaviour far more than knowledge.",
    sections=[
        dict(title="What a base model does", body="""
<p>Ask a raw pretrained model "What is the capital of France?" and a very plausible continuation is:</p>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-sm text-ink-300">What is the capital of France?<br>What is the largest city in Germany?<br>What is the currency of Japan?</p>
<p>It is not being unhelpful. It is doing its job perfectly: on the internet, a question is frequently followed by more questions — a quiz, an FAQ, an exercise list. Answering is only one of many likely continuations.</p>
<p>The base model contains the knowledge and the ability. What it lacks is the <strong>convention</strong> that a user turn should be followed by a helpful assistant turn. Post-training installs that convention, along with tone, refusal behaviour, formatting and much else.</p>
"""),
        dict(title="Stage 1: supervised fine-tuning", body="""
<p>SFT is ordinary next-token training on a curated dataset of conversations. Examples look like:</p>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-xs leading-6 text-ink-300">&lt;|user|&gt; Explain photosynthesis to a 10-year-old.<br>&lt;|assistant|&gt; Plants make their own food using sunlight…&lt;|end|&gt;</p>
<p>Loss is usually computed only on the assistant tokens — you want the model to learn to produce responses, not to produce user turns. Special role tokens delimit the turns and are what let the model track who is speaking. (This is also why prompt-injection attacks are structurally interesting: everything is ultimately one token stream, and the role boundaries are a learned convention rather than a hard barrier.)</p>
<p>Data volume is modest: tens of thousands of examples is often enough, and quality dominates quantity. The LIMA result — strong instruction-following from 1,000 carefully curated examples — is the canonical evidence that SFT is teaching a <em>format</em> the model already has the substance for, not teaching new knowledge.</p>
"""),
        dict(title="Stage 2: learning from preferences", body="""
<p>SFT can only imitate demonstrations. But for many questions, writing an ideal answer is hard while <em>comparing</em> two answers is easy. RLHF exploits that asymmetry.</p>
<ol>
  <li><strong>Collect comparisons.</strong> Sample two responses to the same prompt; a human labels which is better. Repeat for tens or hundreds of thousands of prompts.</li>
  <li><strong>Train a reward model.</strong> A separate network (often initialised from the LLM) learns to output a scalar score, trained so that preferred responses score higher. It is a learned, automatable stand-in for human judgement.</li>
  <li><strong>Optimise the policy.</strong> Use reinforcement learning — PPO — to update the LLM to produce responses the reward model scores highly, with a KL-divergence penalty that punishes drifting too far from the SFT model.</li>
</ol>
<p>That KL penalty is essential. Without it the policy finds adversarial nonsense that the reward model happens to love — classic <strong>reward hacking</strong>. The reward model is an approximation of human preference, and any optimiser pushed hard enough will find where the approximation breaks.</p>
""", figure=fig("viz-preference", "Label preference pairs",
                "Play the annotator: pick the better response, then see what signal your choices give a reward model.")),
        dict(title="DPO and what comes after", body="""
<p>PPO-based RLHF is fiddly: four models in memory at once — the policy being trained, a value network, the reward model and the frozen reference — plus unstable training and many hyperparameters. <strong>Direct Preference Optimisation</strong> showed that the RLHF objective can be rewritten as a simple classification loss directly on preference pairs — no reward model, no RL loop.</p>
<p>The intuition: increase the log-probability of the preferred response and decrease it for the rejected one, each measured relative to a frozen reference model. One model to train, standard supervised machinery, dramatically simpler. DPO and its variants (IPO, KTO, ORPO) are now the default for most open-model post-training, though carefully done PPO can still edge it out at the frontier.</p>
<p>Other things that live in post-training:</p>
<ul>
  <li><strong>Constitutional AI / RLAIF</strong> — a model critiques and revises its own outputs against a written set of principles, replacing much of the human labelling.</li>
  <li><strong>RLVR</strong> — reinforcement learning from <em>verifiable</em> rewards: for maths and code you can check the answer automatically, giving a clean, unhackable reward signal. This is the engine behind current reasoning models.</li>
  <li><strong>Reasoning training</strong> — rewarding long chains of thought that reach verified-correct answers, which produces models that spend far more tokens thinking before answering.</li>
</ul>
<div class="note note-warn"><p class="text-sm"><strong>The alignment tax.</strong> Post-training can reduce raw capability and diversity: models become more cautious, more formulaic, and sometimes over-refuse. It also produces sycophancy, because human raters prefer agreement — an incentive built directly into the objective. There is a genuine trade-off here, not just an engineering bug.</p></div>
"""),
    ],
    exercises=[
        dict(type="mcq",
             prompt="<p>Why does a base pretrained model often respond to a question with more questions?</p>",
             options=["It does not know the answer",
                      "It is completing text, and on the internet a question is frequently followed by more questions",
                      "Its temperature is set too high",
                      "The tokenizer does not recognise question marks"],
             answer="1",
             explain="It has the knowledge; it lacks the convention. Continuation is the only thing it was ever trained to do, and lists of questions are a very common continuation of a question."),
        dict(type="order",
             prompt="<p>Order the stages of a classic RLHF pipeline.</p>",
             items=["Pretrain on a large text corpus",
                    "Supervised fine-tuning on curated conversation demonstrations",
                    "Collect human comparisons between pairs of model responses",
                    "Train a reward model to score responses",
                    "Optimise the policy against the reward model with a KL penalty"],
             explain="Pretrain → SFT → collect preferences → reward model → RL optimisation. DPO collapses the last two into one supervised step."),
        dict(type="mcq",
             prompt="<p>What does the KL-divergence penalty in RLHF prevent?</p>",
             options=["The model from generating too many tokens",
                      "The policy from drifting far from the SFT model and reward-hacking its way to nonsense the reward model overrates",
                      "The reward model from overfitting to the training data",
                      "Gradient explosion during backpropagation"],
             answer="1",
             explain="The reward model is only an approximation of human preference. Unconstrained optimisation finds its blind spots, so you anchor the policy near a known-reasonable starting point."),
        dict(type="mcq",
             prompt="<p>What is the main practical advantage of DPO over PPO-based RLHF?</p>",
             options=["It needs no preference data",
                      "It eliminates the separate reward model and the RL loop, training directly on preference pairs with a supervised loss",
                      "It produces models with more knowledge",
                      "It works without a pretrained base model"],
             answer="1",
             explain="DPO still needs the same preference data. What it removes is the machinery: one training loop, one model to optimise, standard supervised tooling."),
        dict(type="multi",
             prompt="<p>Which are real, documented side effects of post-training? Select all.</p>",
             options=["Sycophancy, because raters tend to prefer agreeable responses",
                      "Reduced output diversity compared with the base model",
                      "Complete removal of factual errors",
                      "Over-refusal of harmless requests that superficially resemble unsafe ones"],
             answer=[0, 1, 3],
             explain="Post-training reshapes behaviour, not knowledge. Hallucination is reduced somewhat by preference training but nowhere close to eliminated."),
        dict(type="fill",
             prompt="<p>What does the acronym SFT stand for in post-training?</p>",
             answer=["supervised fine-tuning", "supervised finetuning", "supervised fine tuning"],
             placeholder="three words",
             explain="Supervised fine-tuning — ordinary next-token training on curated demonstration conversations, with the loss applied to the assistant's tokens."),
    ],
))
