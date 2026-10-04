# -*- coding: utf-8 -*-
"""Part IV — Advanced. Lessons 16-21."""
from codeblocks import block, source

def fig(fid, title, sub, body=""):
    return ('<div class="figure" id="%s">'
            '<p class="figure-title">%s</p>'
            '<p class="figure-sub">%s</p>%s</div>') % (fid, title, sub, body)

Q35 = "Sources/Inference/Qwen35.swift"
GD = "Sources/Inference/GatedDelta.swift"
MTP = "Sources/Inference/MTPGenerator.swift"

LESSONS = []

# ------------------------------------------------------------------ 16
LESSONS.append(dict(
    part="Part IV · Advanced",
    title="Mixture of experts",
    blurb="Replace the MLP with many expert MLPs and a router that picks a few per token. Implement routing, gathered matrix multiplies and expert stacking, and verify them against tiny random checkpoints you can run on any Mac.",
    viz=False,
    goals=[
        "Explain how a mixture-of-experts layer chooses and mixes experts",
        "Implement expert weights as one stacked tensor with gathered matmuls",
        "Explain why prefill sorts tokens by expert",
        "Convert per-expert checkpoint tensors into the stacked layout",
        "Reason about the memory and speed of MoE models on a Mac",
    ],
    recap="An MoE layer scores all experts per token, keeps the top k, and adds their outputs weighted by renormalized scores; Qwen3.5 adds a shared expert every token uses. Expert weights live in one [E, out, in] tensor and gatherMM multiplies each token only by its chosen experts. A 30B-A3B model needs memory for 30B parameters but reads only about 3B per token, so it decodes like a small model if it fits.",
    sections=[
        dict(title="The idea", body="""
<p>A dense model uses every parameter for every token. A <strong>mixture-of-experts</strong> (MoE) model replaces the MLP in some or all blocks with <em>E</em> separate expert MLPs and a small <strong>router</strong>, a linear layer that scores each expert for each token. Only the top <em>k</em> experts run, and their outputs are mixed by the router's scores.</p>
<p>Qwen3-30B-A3B is the standard example: 128 experts per layer, 8 active per token, about 30 billion parameters in total and about 3 billion active. For an inference server on a Mac this is a very interesting trade:</p>
<ul>
<li><strong>Memory</strong> must hold all 30B parameters: about 17 GB at 4.5 bits per weight. That needs a 32 GB Mac.</li>
<li><strong>Bandwidth</strong>, Lesson 2's speed limit, only has to cover the active 3B per token: about 1.7 GB. So it decodes about as fast as a 3B dense model while being much more capable.</li>
</ul>
<p>Unified memory makes Macs unusually good at MoE models: large RAM, moderate bandwidth, which is exactly what an MoE needs.</p>
"""),
        dict(title="Routing", body="""
""" + source("Sources/Inference/SwitchLayers.swift", "final class SparseMoE") + """
<ol>
<li><strong>Score.</strong> The router maps each token's hidden vector to <em>E</em> logits; softmax, in float32, gives probabilities.</li>
<li><strong>Select.</strong> <code>argPartition</code> finds the top <em>k</em> experts per token without sorting all of them.</li>
<li><strong>Renormalize.</strong> With <code>norm_topk_prob</code>, the k selected scores are rescaled to sum to 1.</li>
<li><strong>Run and mix.</strong> Each token goes through its k experts, giving <code>[B, L, k, hidden]</code>; the outputs are weighted by the scores and summed over k.</li>
<li><strong>Shared expert</strong> (Qwen3.5). One more MLP runs for every token, scaled by its own sigmoid gate, and is added. It captures what every token needs, so the routed experts can specialize.</li>
</ol>
<p>The layer conforms to <code>UnaryLayer</code>, so it drops into the <code>mlp</code> slot of a block. In Qwen3 the config decides per layer:</p>
""" + source("Sources/Inference/Qwen3Config.swift", "func isMoELayer") + """
"""),
        dict(title="Experts as one tensor", body="""
<p>Storing 128 separate <code>Linear</code> layers and looping over them per token would be hopelessly slow. Instead, all experts' weights for one projection are one tensor of shape <code>[E, out, in]</code>, and MLX's <code>gatherMM</code> multiplies each input row by the expert matrices its indices name, in one kernel:</p>
""" + source("Sources/Inference/SwitchLayers.swift", "public class SwitchLinear") + source("Sources/Inference/SwitchLayers.swift", "public final class QuantizedSwitchLinear") + """
<p>The layer conforms to <code>Quantizable</code>, so the generic <code>quantize(model:)</code> walk from Lesson 4 turns it into a <code>QuantizedSwitchLinear</code>, whose call uses <code>gatherQuantizedMM</code> on packed 4-bit weights. Three of them make a SwiGLU expert bank:</p>
""" + source("Sources/Inference/SwitchLayers.swift", "final class SwitchGLU") + """
<p>The sorting step matters for prefill. With hundreds of tokens each picking 8 experts, rows for any given expert are scattered all over the batch, and the kernel would load each expert's weights many times. Sorting the (token, expert) pairs by expert makes all rows for one expert contiguous, so its weights are read once; <code>sortedIndices: true</code> tells the kernel it may rely on that. An inverse permutation restores the original order afterwards. During decode there are only k pairs per token, so sorting is skipped below 64 pairs.</p>
"""),
        dict(title="Loading expert weights", body="""
<p>Hugging Face checkpoints store each expert separately: <code>mlp.experts.17.gate_proj.weight</code>, 128 times per projection per layer. The loader stacks them into the layout above before updating the model:</p>
""" + source("Sources/Inference/SwitchLayers.swift", "func stackExperts") + """
<p>Both loaders call it, for the main model and for the MTP head (whose single layer is also MoE in Qwen3.5 MoE models). Pre-converted MLX checkpoints already contain stacked <code>switch_mlp</code> tensors and pass through untouched.</p>
"""),
        dict(title="Verifying without a 30B model", body="""
<p>The real MoE models do not fit on the 8 GB M1 this course was built on. The fix is a standard testing trick: tiny checkpoints with the exact architecture and random weights. <code>yujiepan/qwen3-moe-tiny-random</code> (hidden size 64, 8 experts, top-2, one dense and one MoE layer) and <code>yujiepan/qwen3.5-moe-tiny-random</code> (hidden size 8, 128 experts, top-10, a shared expert, linear attention and an MoE MTP head) are a few megabytes each, but they exercise every code path: routing, stacking, gathered matmuls, sorting during prefill, and the loaders.</p>
""" + block('''qwen3-moe-tiny-random     max |Δ logit| 0.0625   (logits up to 9.9)   argmax agrees at every position
qwen3.5-moe-tiny-random   max |Δ logit| 0.043    (logits up to 1.4)   argmax agrees at every position''', "text") + """
<p>One surprise: Python's <code>mlx-lm</code> could not load the Qwen3.5 tiny checkpoint at all, because its loader expects the experts in a fused layout and this checkpoint stores them per expert. The reference run had to stack them by hand first. Your own loader handling both layouts is a small advantage of writing it yourself.</p>
<p>Random weights make a strict test: there are no learned regularities to hide errors behind, so a wrong routing or a transposed tensor shows up immediately as large differences.</p>
"""),
    ],
    exercises=[
        dict(type="numeric", prompt="<p>A 30B-total, 3B-active MoE model at 4.5 bits per weight. About how many gigabytes are read per decoded token (10<sup>9</sup> bytes; ignore the cache)? One decimal.</p>",
             answer=1.7, tolerance=0.06, placeholder="GB",
             explain="<p>3 × 10<sup>9</sup> × 4.5 / 8 ≈ 1.69 GB. The other 27B parameters sit in memory unused for this token.</p>"),
        dict(type="mcq", prompt="<p>Why are expert weights stored as one [E, out, in] tensor?</p>",
             options=["It saves memory",
                      "One gathered matmul can then multiply each token by just its selected experts, instead of looping over 128 layers",
                      "Safetensors requires it",
                      "Routing needs it"], answer=1,
             explain="<p>gatherMM uses the indices to pick expert matrices inside one kernel.</p>"),
        dict(type="mcq", prompt="<p>Why sort (token, expert) pairs by expert during prefill?</p>",
             options=["To make results deterministic",
                      "So each expert's rows are contiguous and its weights are read once rather than many times",
                      "Routing requires sorted scores",
                      "To drop unused experts"], answer=1,
             explain="<p>It turns scattered accesses into one pass per expert, which is what a bandwidth-bound kernel needs.</p>"),
        dict(type="mcq", prompt="<p>What does Qwen3.5's shared expert do?</p>",
             options=["Replaces the router for short prompts",
                      "Runs for every token, scaled by its own gate, alongside the k routed experts",
                      "Is used only by the MTP head",
                      "Balances load between experts during inference"], answer=1,
             explain="<p>It is an always-on MLP that handles common computation, freeing routed experts to specialize.</p>"),
        dict(type="mcq", prompt="<p>Why test with tiny random-weight checkpoints?</p>",
             options=["They are more accurate",
                      "They have the real architecture but fit anywhere, and random weights make errors obvious",
                      "Real checkpoints cannot be compared",
                      "They decode faster"], answer=1,
             explain="<p>They exercise every code path cheaply, and nothing learned masks a mistake.</p>"),
    ],
))

# ------------------------------------------------------------------ 17
LESSONS.append(dict(
    part="Part IV · Advanced",
    title="Qwen3.5's hybrid architecture",
    blurb="Three of every four Qwen3.5 layers drop softmax attention for Gated DeltaNet, a linear attention whose memory is a fixed-size matrix. Implement it with plain ops, then as a custom Metal kernel, and implement the gated full-attention layers in between.",
    viz=False,
    goals=[
        "Explain linear attention and why its state does not grow with context",
        "Derive the gated delta rule update the code implements",
        "Implement the short causal convolution and its cache",
        "Write the recurrence as a Metal kernel and measure the gain",
        "List every way a Qwen3.5 checkpoint differs from Qwen3 when loading",
    ],
    recap="Gated DeltaNet keeps a per-head matrix S that it decays, corrects toward each new key-value pair, and reads with each query, so per-token cost and memory are constant in context length. Each layer also has a 4-tap causal convolution whose last 3 inputs are cached. A Metal kernel that keeps S in registers across tokens prefills about 3× faster than the op-by-op version. The full-attention layers add an output gate and rotate only a quarter of each head. Loading requires transposing conv weights, adding 1 to most norm weights, and keeping the MTP head.",
    sections=[
        dict(title="Why a hybrid", body="""
<p>Softmax attention's cache grows with every token, and each decode step reads all of it. At long context the cache, not the weights, dominates memory and bandwidth (Lesson 9). <strong>Linear attention</strong> replaces the growing list of keys and values with a fixed-size summary, updated once per token. It is cheaper but loses some ability to recall exact details from far back.</p>
<p>Qwen3.5 mixes the two: of its 24 layers, 18 are Gated DeltaNet (linear) and 6 are full softmax attention, in a repeating pattern of three linear layers then one full. The full-attention layers keep precise long-range recall; the linear layers make everything else cheap. For the 0.8B model, the KV cache is 12 KB per token instead of the 112 KB of Qwen3-0.6B, plus about 19 MB of fixed state.</p>
""" + source("Sources/Inference/Qwen35Config.swift", "public struct Qwen35Config", "    public var ropeParameters: RopeParameters") + """
"""),
        dict(title="The gated delta rule", body="""
<p>Each linear-attention head keeps a matrix <code>S</code> of shape <code>[Dv, Dk]</code> (128×128 here), an associative memory that maps keys to values. For each token, with key <code>k</code>, value <code>v</code> and query <code>q</code>:</p>
""" + block('''S ← g · S                      decay: forget a little of everything (0 < g < 1)
S ← S + β · (v − S k) kᵀ        delta rule: move what S returns for k toward v
y = S q                        read: what does the memory say for this query?''', "text") + """
<p>The middle line is the "delta" in DeltaNet. <code>S k</code> is what the memory currently returns for key <code>k</code>; the update writes only the <em>difference</em> between that and the true value, scaled by a write strength <code>β</code>. Plain linear attention would add <code>v kᵀ</code> blindly and pile up interference; the delta rule corrects instead. The decay <code>g</code> lets the model forget stale content. Both are computed per token and per head from the input:</p>
""" + block('''g = exp(−exp(A_log) · softplus(a + dt_bias))     a = in_proj_a(x),  learned A_log, dt_bias
β = sigmoid(b)                                   b = in_proj_b(x)''', "text") + """
<p>The plain-ops implementation is a direct transcription, compiled into one kernel per step:</p>
""" + source(GD, "let gatedDeltaStep") + source(GD, "func gatedDeltaOps") + """
<p>The state is kept in float32. It accumulates thousands of small updates, and bfloat16's three significant digits would erode it.</p>
"""),
        dict(title="The full layer", body="""
""" + source(Q35, "final class GatedDeltaNet") + """
<p>Around the recurrence:</p>
<ul>
<li><strong>Projections.</strong> <code>in_proj_qkv</code> produces queries, keys and values together; <code>in_proj_z</code> a gate for the output; <code>in_proj_a</code> and <code>in_proj_b</code> the decay and write-strength inputs.</li>
<li><strong>Short convolution.</strong> Before the recurrence, q, k and v pass through a depthwise causal convolution with 4 taps: each channel becomes a learned mix of its last 4 values. This gives the layer cheap access to the immediately preceding tokens. During decode, the last 3 inputs must be remembered, so they are part of the cache alongside <code>S</code>.</li>
<li><strong>Normalization.</strong> q and k are L2-normalized per head, and the 1/√Dk readout scale is folded into q. The code uses <code>rmsNorm</code> with a rescaled epsilon, because RMS norm is L2 norm divided by √Dk.</li>
<li><strong>Heads.</strong> In the tiny MoE test model there are more value heads than key heads, so q and k are repeated to match; the 0.8B model has 16 of each.</li>
<li><strong>Output.</strong> The result is RMS-normalized and multiplied by <code>silu(z)</code> in float32, then projected back to the hidden size.</li>
</ul>
"""),
        dict(title="The cache, and why it cannot rewind", body="""
""" + source("Sources/Inference/LayerCache.swift", "public final class LinearCache") + """
<p>An attention cache can forget the last <em>n</em> tokens by moving its write position back. <code>S</code> cannot: each token's contribution has been decayed and mixed into every entry, and there is no way to subtract it out. That is why Lesson 14's prompt cache matches whole entries only. Speculative decoding (Lesson 19) needs to undo rejected draft tokens, so the cache can optionally keep a snapshot of the state after each token of a step, and <code>trim</code> restores one of them.</p>
"""),
        dict(title="A custom Metal kernel", body="""
<p>The ops version launches a compiled kernel per token per layer, and each launch reads <code>S</code> from memory and writes it back: 1 MB per layer per token for the 0.8B model. During a 512-token prefill that is 512 round trips per layer. The kernel below keeps <code>S</code> in registers for the whole sequence instead:</p>
""" + source(GD, "private let gatedDeltaKernel", '        """') + source(GD, "func gatedDeltaMetal") + """
<p>How the work is split: the grid launches one SIMD group of 32 threads per row of <code>S</code> per head per batch element. Each thread holds <code>Dk / 32</code> entries of its row in registers. For each token the threads decay their entries, compute their share of <code>S k</code> and combine it with <code>simd_sum</code>, apply the delta update, and compute their share of <code>S q</code> the same way. <code>S</code> is read once at the start and written once at the end. The optional <code>history</code> output writes the state after every token; Lesson 19 uses it for rollback.</p>
""" + block('''prefill, 512 tokens, Qwen3.5-0.8B on M1:   Metal kernel 754 ms    plain ops 2323 ms''', "text") + """
<p>The global <code>gatedDeltaUseKernel</code> switch keeps the ops path available as a readable reference to test the kernel against.</p>
"""),
        dict(title="Gated full attention", body="""
""" + source(Q35, "final class GatedAttention") + """
<p>Two differences from Qwen3's attention. <code>q_proj</code> is twice as wide and produces both the queries and a per-channel <strong>output gate</strong>; the attention output is multiplied by <code>sigmoid(gate)</code> before <code>o_proj</code>, letting the model switch a head's contribution off. And RoPE rotates only the first quarter of each 256-dimensional head (<code>partial_rotary_factor</code> 0.25, so 64 dimensions); the rest carry content without position. Qwen3.5's config describes a multimodal rotary scheme (mRoPE) for images and video; for text all its position streams are equal, and it reduces to ordinary RoPE on those 64 dimensions.</p>
"""),
        dict(title="Loading Qwen3.5", body="""
""" + source("Sources/Inference/Qwen35Loader.swift", "public func loadQwen35") + source("Sources/Inference/Qwen35Loader.swift", "private func isShiftedNorm") + """
<p>Every difference from Qwen3 is a trap that produces a working but wrong model:</p>
<ul>
<li><strong>Names.</strong> The checkpoint is a vision-language model: text weights sit under <code>model.language_model.</code> and the vision tower under <code>model.visual.</code>, which is skipped.</li>
<li><strong>Conv weights</strong> are stored PyTorch-style as <code>[out, 1, kernel]</code>; MLX wants <code>[out, kernel, 1]</code>.</li>
<li><strong>Norms.</strong> Qwen3.5's RMSNorms multiply by <code>(1 + w)</code> and store only <code>w</code>, which is near zero. MLX's RMSNorm multiplies by <code>w</code>. Adding 1 at load time fixes it, for every norm except the gated norm inside linear attention, which uses <code>w</code> directly. Forget this and the model loads, runs, and is quietly broken.</li>
<li><strong>The MTP head.</strong> The weights under <code>mtp.</code> are kept. The popular pre-quantized community conversions of Qwen3.5 drop them (their index has zero <code>mtp</code> keys), so this loader starts from the original bfloat16 checkpoint and quantizes every matrix whose width divides into groups of 64 itself. Loading 0.8B this way peaks at about 2 GB of memory before settling at about 0.5 GB.</li>
</ul>
<p>Parity against <code>mlx-lm</code> for the bfloat16 model: the same top token at every position, with differences up to 0.58 at logits around 23, both for full prefill and for token-by-token decoding through the caches.</p>
"""),
    ],
    exercises=[
        dict(type="numeric", prompt="<p>Qwen3.5-0.8B's linear-attention state: 18 layers × 16 heads × 128 × 128 entries in float32. About how many megabytes (10<sup>6</sup> bytes)? Round to the nearest MB.</p>",
             answer=19, tolerance=0.6, placeholder="MB",
             explain="<p>18 × 16 × 16,384 × 4 bytes = 18.9 MB, the same at 10 tokens or 100,000.</p>"),
        dict(type="mcq", prompt="<p>In <code>S ← S + β(v − Sk)kᵀ</code>, what does <code>Sk</code> represent?</p>",
             options=["The attention score", "What the memory currently returns for key k",
                      "The decay factor", "The query projection"], answer=1,
             explain="<p>The delta rule writes only the difference between the stored and the true value for this key.</p>"),
        dict(type="mcq", prompt="<p>Why can't a linear-attention cache simply trim its last 2 tokens?</p>",
             options=["It has no notion of position",
                      "Each token's update has been decayed and mixed into the whole state and cannot be subtracted back out",
                      "Trimming is too slow",
                      "The convolution forbids it"], answer=1,
             explain="<p>The state is a running summary, not a list. Undoing requires a saved earlier state.</p>"),
        dict(type="mcq", prompt="<p>Why is the Metal kernel about 3× faster for prefill than the ops version?</p>",
             options=["It uses lower precision",
                      "It keeps the state in registers for the whole sequence instead of reading and writing it from memory for every token",
                      "It skips the decay",
                      "It runs on the Neural Engine"], answer=1,
             explain="<p>The recurrence is memory-bound when the state round-trips through memory each token.</p>"),
        dict(type="mcq", prompt="<p>A Qwen3.5 port produces fluent but noticeably worse text. Which loading mistake is the most likely culprit?</p>",
             options=["Skipping the vision tower",
                      "Forgetting to add 1 to the (1 + w) RMSNorm weights",
                      "Quantizing to 4 bits",
                      "Keeping the MTP weights"], answer=1,
             explain="<p>Without the +1, every norm scales by a value near zero instead of near one. The model still produces text, which is what makes this mistake dangerous.</p>"),
    ],
))

# ------------------------------------------------------------------ 18
LESSONS.append(dict(
    part="Part IV · Advanced",
    title="Speculative decoding",
    blurb="Guess several tokens cheaply, then check them all with one pass of the real model. Learn the acceptance rule that keeps output exactly as good as normal decoding, and the cost model that says when it actually speeds things up.",
    viz=True,
    goals=[
        "Explain draft-then-verify and why verification is nearly free when decode is bandwidth-bound",
        "Apply the greedy acceptance rule",
        "Apply rejection sampling so sampled output keeps the target model's distribution",
        "Predict the speed-up from acceptance rate and relative costs",
    ],
    recap="A cheap drafter proposes tokens; the target model scores the last committed token plus the drafts in one pass. Greedy: accept a draft if it equals the target's choice. Sampling: accept draft d with probability min(1, p(d)/q(d)), otherwise draw from the normalized leftover max(0, p − q); this yields exactly the target distribution. With acceptance rate α and one draft per step, each step emits 1 + α tokens on average, and the speed-up is (1 + α) divided by the cost of a verify step plus a draft, in units of a normal step.",
    sections=[
        dict(title="The idea", body="""
<p>Lesson 2's table again: a single-sequence decode step barely uses the GPU's arithmetic. Running the model on 2 or 3 tokens instead of 1 reads the same weights and, ideally, costs about the same. Prefill already exploits this. Can decode?</p>
<p>The obstacle is that decode is sequential: token <em>n+1</em> depends on token <em>n</em>. <strong>Speculative decoding</strong> gets around it by guessing:</p>
<ol>
<li>A cheap <strong>drafter</strong> proposes the next token, or the next few.</li>
<li>The real model, the <strong>target</strong>, runs once on the last committed token followed by the drafts. Because a transformer produces logits at every position, this one pass gives the target's prediction after each draft as well.</li>
<li>Compare: keep the drafts the target agrees with, plus one token from the target itself at the first disagreement or after the last draft.</li>
</ol>
<p>Every step emits at least one token, the same one normal decoding would have produced, and sometimes more. The drafter can be a small separate model, a lookup in the prompt, or, in Qwen3.5's case, a tiny head built into the model itself (next lesson).</p>
"""),
        dict(title="Greedy acceptance", body="""
<p>With greedy decoding the rule is simple. Suppose the last committed token is <code>t</code> and the drafter proposes <code>d</code>. The target runs on <code>[t, d]</code> and returns two sets of logits:</p>
<ul>
<li>at position 0: what should follow <code>t</code>. Call its argmax <code>a₀</code>.</li>
<li>at position 1: what should follow <code>d</code>. Call its argmax <code>a₁</code>.</li>
</ul>
<p>If <code>a₀ = d</code>, the draft was right: emit <code>d</code> and also <code>a₁</code>, two tokens for one pass. If not, emit <code>a₀</code>, which is what plain greedy decoding would have chosen, and discard everything computed for <code>d</code>, including its entries in the caches.</p>
<p>The output is identical to plain greedy decoding, in principle token for token. In practice the two-token pass uses a different kernel shape than the one-token pass, so a near-tie can occasionally flip (Lesson 8). Lesson 19 shows exactly such a case.</p>
"""),
        dict(title="Sampling without changing the distribution", body="""
<p>With temperature above zero, "is the draft right?" has no yes/no answer. Let <code>q</code> be the drafter's distribution and <code>p</code> the target's, both after the same temperature and truncation (that is why the sampler in Lesson 10 exposes <code>logProbabilities</code>). The draft <code>d</code> was drawn from <code>q</code>. Then:</p>
<ol>
<li>Accept <code>d</code> with probability <code>min(1, p(d) / q(d))</code>.</li>
<li>If rejected, draw a replacement from the leftover distribution <code>max(0, p − q)</code>, normalized.</li>
</ol>
<p>Why this is exact: the chance of ending with token <em>x</em> is the chance it was drafted and accepted, <code>q(x) · min(1, p(x)/q(x)) = min(q(x), p(x))</code>, plus the chance of a rejection times the leftover's probability for <em>x</em>. The total rejection probability is <code>1 − Σ min(p, q) = Σ max(0, p − q)</code>, which is exactly the normalizer of the leftover, so the second term is <code>max(0, p(x) − q(x))</code>. Adding them, <code>min(q, p) + max(0, p − q) = p(x)</code>. The output is distributed exactly as if the target had sampled alone. Where the drafter overestimates a token, some of its drafts are rejected; where it underestimates one, the leftover makes up the difference.</p>
"""),
        dict(title="When it is faster", body="""
<p>Let <code>α</code> be the acceptance rate with one draft per step. Each step then emits <code>1 + α</code> tokens on average. Measure costs in units of one normal decode step:</p>
<ul>
<li><code>c_verify</code>: the target pass on 2 tokens. Ideally about 1, if the step really is bandwidth-bound.</li>
<li><code>c_draft</code>: producing the draft.</li>
</ul>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-sm text-ink-100">speed-up = (1 + α) / (c_verify + c_draft)</p>
<p>With α = 0.9, c_verify = 1.0 and c_draft = 0.15, the speed-up is 1.9 / 1.15 ≈ 1.65. But if the 2-token pass costs 1.4 normal steps, it drops to 1.9 / 1.55 ≈ 1.23, and at 2.2 the "speed-up" is a slowdown. <strong>c_verify is the number that decides everything</strong>, and Lesson 15 already measured that it depends on the matmul kernel and the weight precision. Explore the trade-off below.</p>
<p>With <em>k</em> drafts per step, the expected tokens per step become <code>(1 − α^(k+1)) / (1 − α)</code>, but c_verify and c_draft grow with k too. Drafters that are only trained to look one token ahead, like Qwen3.5's, use k = 1.</p>
""", figure=fig("viz-speculative", "Speculative decoding speed-up",
                "Set the acceptance rate and the relative costs, or load one of the configurations measured on the M1 in Lesson 19.")),
    ],
    exercises=[
        dict(type="mcq", prompt="<p>Greedy speculative step: committed token t, draft d. The target's argmax after t is d, and after d it is e. What is emitted?</p>",
             options=["d", "e", "d then e", "t then d"], answer=2,
             explain="<p>The draft is confirmed, and the second position's prediction comes free from the same pass.</p>"),
        dict(type="numeric", prompt="<p>q(d) = 0.5 and p(d) = 0.2. With what probability is the draft accepted?</p>",
             answer=0.4, tolerance=0.001, placeholder="probability",
             explain="<p>min(1, 0.2 / 0.5) = 0.4.</p>"),
        dict(type="numeric", prompt="<p>α = 0.8, c_verify = 1.2, c_draft = 0.2. What is the speed-up? (Two decimals.)</p>",
             answer=1.29, tolerance=0.006, placeholder="×",
             explain="<p>(1 + 0.8) / (1.2 + 0.2) = 1.8 / 1.4 ≈ 1.29.</p>"),
        dict(type="mcq", prompt="<p>Why must the drafter and the target use the same temperature and truncation for rejection sampling?</p>",
             options=["Otherwise the code crashes",
                      "p and q must be the distributions the tokens are actually drawn from; otherwise the acceptance rule no longer reproduces the target's sampling distribution",
                      "It makes drafts faster",
                      "It is only a convention"], answer=1,
             explain="<p>The exactness argument relies on q being the drafting distribution and p the distribution plain sampling would use.</p>"),
        dict(type="mcq", prompt="<p>Which single quantity most often decides whether speculative decoding helps on a given machine?</p>",
             options=["Vocabulary size", "The cost of the multi-token verify pass relative to a normal step",
                      "The tokenizer", "The prompt length"], answer=1,
             explain="<p>Acceptance rates of 0.8 to 0.9 are common. Whether the verify pass is really almost free is what varies between hardware, kernels and precisions.</p>"),
    ],
))

# ------------------------------------------------------------------ 19
LESSONS.append(dict(
    part="Part IV · Advanced",
    title="MTP: Qwen3.5's built-in drafter",
    blurb="Every Qwen3.5 checkpoint ships a one-layer head trained to predict two tokens ahead. Wire it up as the drafter, roll back linear-attention state on rejection, remove the hidden GPU waits, and measure where it pays off.",
    viz=False,
    goals=[
        "Explain what the MTP head computes and what it takes as input",
        "Implement the MTP speculative loop: prefill, draft, verify, commit or roll back",
        "Roll back Gated DeltaNet state using per-token snapshots from the kernel",
        "Structure a step so it synchronizes with the GPU once",
        "Interpret the measured speed-ups at 4, 8 and 16 bits",
    ],
    recap="The MTP head combines the main model's final hidden state at position t with the embedding of token t+1, runs one full-attention block, and predicts token t+2 through the shared output projection. The generator drafts one token per step with it, verifies with a 2-token target pass, and on rejection trims the KV caches and restores linear-attention snapshots that the kernel recorded. On a base M1 the drafter is accepted 84 to 92% of the time; the speed-up is 1.31× at 8 bits, while at 4 bits and bf16 the 2-token pass is too expensive to win.",
    sections=[
        dict(title="A drafter inside the model", body="""
<p>Separate draft models have problems: they must share the tokenizer, they cost memory, and their predictions often differ from the target's. Qwen3.5 avoids all of this. It was trained with a <strong>multi-token prediction</strong> (MTP) objective: besides predicting token t+1 from position t, a small extra head learned to predict token t+2. That head ships in every checkpoint as 15 tensors under <code>mtp.</code>.</p>
""" + source("Sources/Inference/MTPHead.swift", "public final class MTPHead") + """
<p>Its input is a pair for each position <em>t</em>:</p>
<ul>
<li>the main model's <strong>final hidden state</strong> at <em>t</em> (after the last norm, the same vector the output projection reads), which already encodes what comes next; and</li>
<li>the <strong>embedding of token t+1</strong>, which tells the head which of the possible next tokens actually came.</li>
</ul>
<p>Both are RMS-normalized, concatenated, projected back to the hidden size by <code>fc</code>, and passed through one full-attention decoder block with its own small KV cache. The main model's output projection turns the result into logits for token t+2. The head reuses the main model's embedding table and output projection, so it adds only one block's worth of weights.</p>
"""),
        dict(title="The generator", body="""
""" + source(MTP, "public struct MTPGenerator", "    /// Runs the MTP head on newly committed", include_end=False) + """
<p><strong>Prefill</strong> runs the main model over the prompt, keeping the hidden states, and samples the first token. Then it prefills the MTP head: position <em>i</em> pairs hidden state <em>i</em> with the token at <em>i+1</em>, so the head's token inputs are the prompt shifted left by one, with the first generated token appended. The head's output at the last position is the first draft.</p>
""" + source(MTP, "    mutating func propose(") + """
"""),
        dict(title="A step", body="""
""" + source(MTP, "    mutating func step()") + source(MTP, "    mutating func verify(") + """
<p>Each step runs the target on <code>[last, draft]</code> and then branches:</p>
<ul>
<li><strong>Accepted</strong>: emit the draft and the bonus token from position 1. Both positions are now committed, so the MTP head reads both (token, hidden state) pairs and drafts the token after the bonus.</li>
<li><strong>Rejected</strong>: every cache holds one position too many, the draft's. Trim them all by one, emit the correction, and let the MTP head read the single committed pair.</li>
</ul>
<p><code>verify</code> implements Lesson 18's rules: an argmax comparison for greedy decoding, rejection sampling otherwise, both written as lazy array expressions.</p>
"""),
        dict(title="Rolling back linear attention", body="""
<p>Trimming a KV cache is one integer (Lesson 9). Trimming Gated DeltaNet state is impossible (Lesson 17). So before the verify pass, the generator sets <code>recordSnapshots</code> on every linear cache, and the layer asks the kernel for its <code>history</code> output: the state after each of the two tokens. The convolution window after each token is a slice of the convolution input. On rejection, <code>trim(1)</code> restores the snapshot taken after the first token, <code>last</code>, which is exactly the committed state.</p>
<p>The first version recorded snapshots with the plain-ops recurrence, which keeps per-token states naturally. Measured in a Debug build, that made the 2-token verify pass cost 49 ms against 34 ms for the kernel path, more than the second token itself. Adding the history output to the kernel brought it to 36 ms. In Release the snapshot overhead is about 1 ms on a 17 ms pass.</p>
"""),
        dict(title="One sync per step", body="""
<p>Lesson 3 warned that every <code>item()</code> makes the CPU wait for the GPU. The first sampled-mode implementation read the acceptance ratio, the draft, the correction and the bonus token with separate <code>item()</code> calls, four waits per step, and it was slower than plain decoding: 30.8 tokens per second against 35.0 (Debug).</p>
<p>The version above builds the accept decision, the correction and the bonus token as one lazy graph and evaluates it once, with <code>eval(ok, correction, bonus, draft)</code>, before reading any of them. Sampled-mode throughput rose to 44.3 tokens per second, now faster than plain. Computing a correction or bonus that ends up unused costs a few microseconds of GPU time; each avoided synchronization saves far more.</p>
"""),
        dict(title="Results on a base M1", body="""
<p>Qwen3.5-0.8B, 256 tokens of a coding answer, Release build:</p>
""" + block('''weights   plain       MTP         speed-up   acceptance   1-token pass   2-token pass
4-bit     92.5 tok/s  87.3 tok/s  0.94×      87%          12.2 ms        16.8 ms
8-bit     50.9 tok/s  66.8 tok/s  1.31×      92%          18.6 ms        18.6 ms
bf16      31.8 tok/s  24.9 tok/s  0.78×      92%          30.1 ms        65.0 ms''', "text") + """
<p>The acceptance rate is excellent everywhere: the head agrees with the main model about nine times in ten. What decides the outcome is the last two columns, Lesson 18's c_verify, and they match the kernel measurements from Lesson 15. At 8 bits, two rows cost the same as one, so the second token really is free. At 4 bits, the 2-token pass costs 1.4 normal steps; add about 3 ms for the head (mostly its pass through the 248,000-row output projection) and there is no gain left. In bf16 the multi-row kernel costs 2.2 normal steps.</p>
<p>So on this machine the best configuration for single-user latency is 8-bit weights with MTP: 67 tokens per second at higher precision than 4-bit. Plain 4-bit is faster still but less accurate. On chips with more compute per byte of bandwidth, or on larger models where each step is more firmly bandwidth-bound, the 2-token pass gets cheaper relative to one token, and MTP gains grow. Measure on your hardware with <code>infer &lt;model&gt; bench</code> before choosing.</p>
"""),
        dict(title="Checking correctness", body="""
<p>Greedy MTP output should equal plain greedy output. For the coding prompt, the two agree for 13 tokens and then diverge. At that point the plain model's top two logits are <code>" Check" 20.375</code> and <code>" Checks" 20.375</code>, an exact tie in bfloat16, and the 2-token pass's slightly different rounding breaks it the other way. Everything else checks out: acceptance rates near 90% are only possible if the head's inputs (the post-norm hidden state, the shifted tokens, the shared projection) are wired correctly, and a wrong pairing drops acceptance close to zero.</p>
<p>Two things to remember when running MTP in the server: it is used only by the serial engine (batching and speculation compete for the same spare rows in the matmul), and it currently bypasses the prompt cache (Lesson 14).</p>
"""),
    ],
    exercises=[
        dict(type="mcq", prompt="<p>What does the MTP head receive for position t?</p>",
             options=["The prompt text", "The main model's final hidden state at t and the embedding of token t+1",
                      "Only the logits at t", "The KV cache of the last layer"], answer=1,
             explain="<p>The hidden state says what is likely next; the embedding says what actually came next. Together they let the head predict t+2.</p>"),
        dict(type="mcq", prompt="<p>A draft is rejected. What happens to the Gated DeltaNet caches?</p>",
             options=["Nothing; they are recomputed next step",
                      "They are restored to the snapshot taken after the first token of the verify pass",
                      "They are cleared",
                      "Their offset is decremented, like a KV cache"], answer=1,
             explain="<p>The kernel recorded the state after each token. Restoring the first snapshot removes the draft's contribution exactly.</p>"),
        dict(type="numeric", prompt="<p>Using the 8-bit row of the table: plain 50.9 tok/s, MTP 66.8 tok/s. What is the speed-up? (Two decimals.)</p>",
             answer=1.31, tolerance=0.006, placeholder="×",
             explain="<p>66.8 / 50.9 ≈ 1.31.</p>"),
        dict(type="mcq", prompt="<p>Why is MTP slower than plain decoding at 4 bits on the M1 despite 87% acceptance?</p>",
             options=["The head is inaccurate at 4 bits",
                      "The 2-token verify pass costs about 1.4 normal steps, and the draft adds about 0.25 more, so 1.87 tokens cost about 1.65 steps or more",
                      "Quantization breaks rollback",
                      "The tokenizer is slower"], answer=1,
             explain="<p>Lesson 18's formula: 1.87 / (1.38 + 0.25) ≈ 1.15 at best in theory, and per-step overheads take the rest.</p>"),
        dict(type="mcq", prompt="<p>Why did merging four item() calls into one eval make sampled MTP faster?</p>",
             options=["item() is inaccurate",
                      "Each item() is a CPU–GPU synchronization; one combined evaluation waits once per step instead of four times",
                      "eval uses a faster kernel",
                      "It reduced memory use"], answer=1,
             explain="<p>Synchronizations serialize CPU and GPU. Batching the reads into one evaluation removes three of them.</p>"),
    ],
))

# ------------------------------------------------------------------ 20
LESSONS.append(dict(
    part="Part IV · Advanced",
    title="Performance engineering",
    blurb="Measure before optimizing, and measure correctly. Collect every performance lesson from building this server into one method: what to time, how to keep the numbers honest, and which changes actually moved them.",
    viz=False,
    goals=[
        "Benchmark inference code without fooling yourself",
        "Break a decode step into components and time each one",
        "Know which optimizations paid off in this server, and by how much",
        "Keep memory use under control on a small machine",
    ],
    recap="Measure Release builds, warm up, synchronize with eval, repeat, and watch for thermal and system noise. Time components in isolation: the 1-token and 2-token passes, the output projection, the drafter, single kernels at different row counts. In this server the big wins were Release over Debug (2.5×), the custom linear-attention kernel (3× prefill), CPU/GPU pipelining (11%), removing GPU synchronizations, and choosing weight precision to suit the kernels.",
    sections=[
        dict(title="Keep the numbers honest", body="""
<p>Every misleading number met while building this course came from one of these:</p>
<ul>
<li><strong>Debug builds.</strong> 36 vs 89 tokens per second for the same decode. Debug inflates CPU overhead, which changes not just absolute numbers but conclusions: MTP looked like a 1.4× win in Debug and was a slowdown at 4 bits in Release.</li>
<li><strong>Laziness.</strong> Timing code that builds a graph without evaluating it measures nothing. Every timed region must end in <code>eval</code> or <code>item</code>.</li>
<li><strong>Warm-up.</strong> The first call to a kernel includes compiling and caching it. The 4096×4096 matmul in Lesson 3 took 298 ms cold and 94 ms warm.</li>
<li><strong>Noise.</strong> The M1 in a fanless laptop throttles when hot; repeated runs varied by about ±10%. Once, a run reversed a result entirely, while the disk was nearly full and the system was paging. Repeat measurements, alternate the variants you compare, and look at all runs, not the best one.</li>
</ul>
"""),
        dict(title="Time the parts", body="""
<p>End-to-end tokens per second tells you that something is slow, not what. The <code>infer</code> tool's <code>bench</code> mode times the components of a speculative step separately:</p>
""" + source("Sources/infer/main.swift", 'if mode == "bench"') + """
""" + block('''Release, Qwen3.5-0.8B 4-bit, base M1:
target 1 token              12.0 ms
target 2 tokens             16.8 ms
target 2 tokens + snapshots 17.9 ms
MTP head + output proj.      3.0 ms
output projection only       2.6 ms''', "text") + """
<p>Two findings fall straight out. The output projection alone is 2.6 ms of a 12 ms step, 22%: Qwen3.5's 248,320-token vocabulary is expensive, for the main model and for the drafter. And the 2-token pass costs 1.4× one token, which sent the investigation down to single kernels:</p>
""" + block('''mx.quantized_matmul, 14336×1024 weight, average over many calls:
rows   4-bit     8-bit     bf16
1      142 µs    266 µs     482 µs
2      248 µs    266 µs    1225 µs
8      831 µs    833 µs    1227 µs''', "text") + """
<p>That one table explains the batching results in Lesson 15 and the MTP results in Lesson 19. When a result surprises you, keep zooming in until a measurement explains it.</p>
"""),
        dict(title="What paid off", body="""
<table>
<tr><th>Change</th><th>Effect (base M1)</th><th>Lesson</th></tr>
<tr><td>Release instead of Debug build</td><td>36 → 89 tok/s</td><td>3</td></tr>
<tr><td>Metal kernel for the gated delta recurrence</td><td>512-token prefill 2323 → 754 ms</td><td>17</td></tr>
<tr><td>Kernel history output for rollback snapshots</td><td>2-token verify +15 ms → +1 ms</td><td>19</td></tr>
<tr><td>Queue step n+1 before reading token n (asyncEval)</td><td>12.15 → 10.9 ms per token</td><td>9</td></tr>
<tr><td>One synchronization per speculative step</td><td>sampled MTP 30.8 → 44.3 tok/s (Debug)</td><td>19</td></tr>
<tr><td>8-bit weights for MTP</td><td>MTP 0.94× → 1.31× over plain</td><td>19</td></tr>
<tr><td>Prompt cache with the right snapshot point</td><td>turn-2 time to first token 3.25 → 0.97 s</td><td>14</td></tr>
<tr><td>Cancellation on disconnect</td><td>next request served in 0.2 s instead of waiting</td><td>12</td></tr>
</table>
<p>The pipelining measurement, repeated five times in alternation, was the most stable result in the course: 10.8 to 11.0 ms per token with pipelining, 12.1 to 12.2 without.</p>
""" + source("Sources/infer/main.swift", 'if mode == "perf"', "    // 2. Prefill 512 tokens", include_end=False) + """
"""),
        dict(title="Memory", body="""
<p>On an 8 GB machine, memory is as much a constraint as speed. The numbers to know:</p>
<ul>
<li><strong>Loading peaks above steady state.</strong> Quantizing on load reads the bfloat16 weights first: Qwen3.5-0.8B peaks at about 2 GB and settles at about 0.5 GB. A pre-quantized checkpoint avoids the peak but, for Qwen3.5, loses the MTP head.</li>
<li><strong>MLX keeps freed buffers.</strong> For speed, MLX caches GPU buffers it has freed rather than returning them to the system. The engine calls <code>MLX.Memory.clearCache()</code> after each request so a long prompt's temporary buffers do not stay allocated forever. <code>MLX.Memory.activeMemory</code> and <code>peakMemory</code> report usage; log them during load tests.</li>
<li><strong>Caches dominate at long context.</strong> Lesson 9's calculator. The prompt cache multiplies it: four stored long conversations can outweigh the model.</li>
</ul>
<p>For a deeper view, Xcode's Instruments has a Metal System Trace template that shows every kernel on the GPU timeline, which is how you would find, for example, gaps where the GPU waits for the CPU.</p>
"""),
    ],
    exercises=[
        dict(type="mcq", prompt="<p>You time <code>let y = model(x, caches: c)</code> with no eval afterwards and get 0.05 ms. What did you measure?</p>",
             options=["A very fast model", "Only the time to build the lazy graph; the GPU work has not happened",
                      "The cache lookup", "The kernel compile time"], answer=1,
             explain="<p>Without eval or item, MLX has done nothing yet.</p>"),
        dict(type="numeric", prompt="<p>The output projection takes 2.6 ms of a 12.0 ms decode step. What percentage is that? (Nearest whole percent.)</p>",
             answer=22, tolerance=0.6, placeholder="%",
             explain="<p>2.6 / 12.0 ≈ 21.7%, about 22%. A large vocabulary is a real cost at small model sizes.</p>"),
        dict(type="mcq", prompt="<p>Two variants measure 11.2 and 10.6 ms per token in one run each, on a fanless laptop. What should you conclude?</p>",
             options=["The second is 5% faster",
                      "Nothing yet; repeat both several times, alternating, because thermal noise is around ±10%",
                      "The first is broken",
                      "Switch to Debug for stable numbers"], answer=1,
             explain="<p>A difference smaller than the run-to-run noise needs repeated, interleaved measurements before it means anything.</p>"),
        dict(type="mcq", prompt="<p>Why does the engine call MLX.Memory.clearCache() after each request?</p>",
             options=["To reset the model weights",
                      "MLX keeps freed GPU buffers for reuse; clearing returns a long request's temporary buffers to the system",
                      "To empty the prompt cache",
                      "To force recompiling kernels"], answer=1,
             explain="<p>Buffer caching is a speed optimization that would otherwise keep peak allocations alive.</p>"),
    ],
))

# ------------------------------------------------------------------ 21
LESSONS.append(dict(
    part="Part IV · Advanced",
    title="Production: tools, metrics and deployment",
    blurb="Finish the server: tool calling in both Qwen formats, streamed correctly; Prometheus metrics; running it as a service; and an honest list of what a production deployment would still need.",
    viz=False,
    goals=[
        "Pass tool definitions through the chat template and parse tool calls from both Qwen formats",
        "Stream responses that may turn into tool calls without leaking partial markup",
        "Expose metrics that answer the operational questions",
        "Run the server as a background service on macOS",
        "Know what is missing for a multi-user deployment",
    ],
    recap="Tools go into the chat template; the model answers with &lt;tool_call&gt; blocks, JSON in Qwen3 and XML-like tags in Qwen3.5, which the parser turns into OpenAI tool_calls. While streaming, text is buffered from the first possible '&lt;tool_call&gt;' so markup never reaches the client. Counters for requests, rejections, cancellations, tokens and time to first token answer most operational questions. launchd keeps the server running. Authentication, a memory budget and structured output are the next steps.",
    sections=[
        dict(title="Tool calling", body="""
<p>A client describes functions the model may call; the model decides to call one by emitting a structured block instead of text; the client runs the function and sends the result back as a <code>tool</code> message. The server's part is to render the tools into the prompt and recognize calls in the output.</p>
<p>Rendering is done by the chat template, which already knows the model's trained format. Qwen3.5's template, for instance, lists the tools as JSON inside <code>&lt;tools&gt;</code> and instructs the model to reply with:</p>
""" + block('''<tool_call>
<function=get_weather>
<parameter=city>
Oslo
</parameter>
</function>
</tool_call>''', "text") + """
<p>Qwen3 uses JSON inside the same tags: <code>&lt;tool_call&gt;{"name": "get_weather", "arguments": {"city": "Oslo"}}&lt;/tool_call&gt;</code>. The parser accepts both:</p>
""" + source("Sources/Inference/ToolCalls.swift", "public enum ToolCallParser") + """
<p>Parameter values in the XML format are plain text, so the parser keeps numbers, booleans and objects typed when they parse as JSON (<code>3</code> becomes <code>3</code>, not <code>"3"</code>). The output is the OpenAI shape, with <code>arguments</code> as a JSON string. Going the other way, clients send earlier tool calls back with string arguments, and the template wants objects, so the route converts them:</p>
""" + source("Sources/serve/OpenAI.swift", "func templateMessage(") + """
<p>The unit tests cover both formats, and a full round trip against Qwen3.5-0.8B works: asked for the weather in Oslo, the model calls <code>get_weather({"city":"Oslo"})</code>, receives <code>{"temp_c": -3, "sky": "snow"}</code>, and answers "The weather in Oslo is currently cold and snowy, with a temperature of -3°C."</p>
"""),
        dict(title="Streaming tool calls", body="""
<p>Streaming makes tool calls harder: the client must not receive <code>&lt;tool_call&gt;&lt;function=get_wea</code> as content. The route in Lesson 12 handles this when the request includes tools. As soon as streamed text contains a <code>&lt;</code>, it starts buffering. If the buffer turns out not to be the start of <code>&lt;tool_call&gt;</code>, it is released as ordinary content. If it is, buffering continues to the end, and the parsed calls go out as one <code>tool_calls</code> delta with <code>finish_reason: "tool_calls"</code>:</p>
""" + block('''data: {"choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call_28389224","type":"function",
       "function":{"name":"get_weather","arguments":"{\\"city\\":\\"Paris\\"}"}}]}}]}
data: {"choices":[{"index":0,"delta":{},"finish_reason":"tool_calls"}]}''', "text") + """
<p>OpenAI streams call arguments in fragments; sending a complete call in one delta is also valid, and every client accepts it.</p>
"""),
        dict(title="Metrics", body="""
<p>The questions an operator asks are: is it up, how loaded is it, are clients being turned away, how long do they wait for the first token, and is the prompt cache working. A few counters answer them, exposed at <code>/metrics</code> in Prometheus' text format:</p>
""" + source("Sources/serve/Metrics.swift", "final class Metrics") + """
<p>The route records them by wrapping each request's event stream, so neither the engines nor the HTTP code needed changing:</p>
""" + source("Sources/serve/main.swift", "func instrument(") + """
""" + block('''qwenserve_requests_total 3
qwenserve_rejected_total 0
qwenserve_cancelled_total 0
qwenserve_prompt_tokens_total 886
qwenserve_cached_prompt_tokens_total 0
qwenserve_completion_tokens_total 69
qwenserve_time_to_first_token_seconds_sum 1.556
qwenserve_time_to_first_token_seconds_count 3
qwenserve_decode_seconds_total 1.048
qwenserve_in_flight 0''', "text") + """
<p>Average time to first token is <code>sum / count</code>; decode speed is completion tokens divided by decode seconds; the cache hit rate is cached prompt tokens over prompt tokens. A disconnected client never sees its <code>.finished</code> event, so the wrapper counts a stream that ends without one as cancelled.</p>
"""),
        dict(title="Running as a service", body="""
<p>Build in Release, copy the binary somewhere stable, and let <code>launchd</code> start it at login and restart it if it exits:</p>
""" + block('''<?xml version="1.0" encoding="UTF-8"?>
<!-- ~/Library/LaunchAgents/local.qwenserve.plist -->
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>local.qwenserve</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/serve</string>
    <string>/Users/you/models/Qwen3.5-0.8B</string>
    <string>--bits</string><string>8</string>
    <string>--port</string><string>8080</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/tmp/qwenserve.log</string>
  <key>StandardErrorPath</key><string>/tmp/qwenserve.log</string>
</dict>
</plist>''', "text") + block('''launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.qwenserve.plist
curl -s localhost:8080/health        # ok
launchctl bootout gui/$(id -u)/local.qwenserve   # stop it''', "shell") + """
<p>The MLX Metal library is a bundle next to the binary (<code>mlx-swift_Cmlx.bundle</code>); copy it along with the executable, or the server fails the first time it touches the GPU.</p>
"""),
        dict(title="What is still missing", body="""
<p>The server is complete for one person or a small trusted group on one machine. Before exposing it more widely, add:</p>
<ul>
<li><strong>Authentication and TLS.</strong> Put it behind a reverse proxy that checks API keys and terminates TLS, and keep it bound to localhost.</li>
<li><strong>A memory budget.</strong> Limit total cache memory across running requests and prompt-cache entries, and reject or queue requests whose context would exceed it, instead of discovering the limit by running out of memory.</li>
<li><strong>Structured output.</strong> JSON-schema-constrained generation works by masking, at every step, the logits of tokens that would make the output invalid. The sampler from Lesson 10 is the place to add the mask; the hard part is a grammar engine that computes the allowed tokens quickly.</li>
<li><strong>Reasoning content.</strong> With thinking enabled, separate the <code>&lt;think&gt;</code> block into its own field (several clients expect <code>reasoning_content</code>) rather than mixing it into the answer.</li>
<li><strong>Several models</strong>, loaded on demand and evicted under memory pressure, with the model chosen by the request's <code>model</code> field.</li>
</ul>
<p>You now have every piece: model code you can prove correct, caches for two kinds of attention, a scheduler for one GPU and many clients, two ways to make decode faster, and a method for measuring what each change is worth on the hardware in front of you.</p>
"""),
    ],
    exercises=[
        dict(type="mcq", prompt="<p>Why does the streaming route buffer text once a '&lt;' appears in a request that has tools?</p>",
             options=["To compress the output",
                      "It may be the start of a &lt;tool_call&gt; block, which must reach the client as a structured tool call, not as partial text",
                      "To reduce the number of events",
                      "HTML escaping"], answer=1,
             explain="<p>If the buffer proves not to be a tool call, it is released as content; otherwise the calls are parsed and sent at the end.</p>"),
        dict(type="mcq", prompt="<p>A Qwen3.5 parameter value is written as <code>3</code> inside a <code>&lt;parameter=days&gt;</code> block. What does the parser put in the arguments JSON?</p>",
             options=["\"3\" (a string)", "3 (a number)", "nothing", "an error"], answer=1,
             explain="<p>Values that parse as JSON numbers, booleans or objects keep their type; other text stays a string.</p>"),
        dict(type="numeric", prompt="<p>From the metrics sample: time to first token sum 1.556 s over 3 requests. What is the average, in seconds? (Two decimals.)</p>",
             answer=0.52, tolerance=0.006, placeholder="s",
             explain="<p>1.556 / 3 ≈ 0.52 s.</p>"),
        dict(type="multi", prompt="<p>Which should be added before exposing the server to untrusted users? Select all that apply.</p>",
             options=["Authentication", "A limit on total cache memory", "A bigger vocabulary", "TLS"], answer=[0, 1, 3],
             explain="<p>Access control, encryption and resource limits are the gaps. The vocabulary belongs to the model.</p>"),
    ],
))
