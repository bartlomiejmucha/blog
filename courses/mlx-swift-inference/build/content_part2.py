# -*- coding: utf-8 -*-
"""Part II — Running Qwen. Lessons 6-10."""
from codeblocks import block, source

def fig(fid, title, sub, body=""):
    return ('<div class="figure" id="%s">'
            '<p class="figure-title">%s</p>'
            '<p class="figure-sub">%s</p>%s</div>') % (fid, title, sub, body)

LESSONS = []

# ------------------------------------------------------------------ 6
LESSONS.append(dict(
    part="Part II · Running Qwen",
    title="Tokenizer and chat template",
    blurb="The model only sees integers. Turn chat messages into exactly the token sequence Qwen was trained on, and turn generated tokens back into text that can be streamed safely.",
    viz=False,
    goals=[
        "Explain what the tokenizer files contain and which library uses them",
        "Render a conversation with Qwen's chat template, with and without thinking",
        "Choose the right set of end-of-sequence tokens",
        "Stream text from tokens without breaking multi-byte characters",
        "Implement stop strings that never leak a partial match",
    ],
    recap="swift-transformers loads the tokenizer and renders the Jinja chat template stored in the checkpoint. Qwen uses ChatML: each turn is wrapped in <|im_start|>role … <|im_end|>, and a turn ends when the model emits <|im_end|>. Streaming needs care because one token is not one character: decode a window, hold back incomplete characters, and hold back text that could be the start of a stop string.",
    sections=[
        dict(title="From text to ids", body="""
<p>Qwen uses byte-level BPE: text is turned into UTF-8 bytes, and frequent byte sequences are merged into tokens according to the rules in <code>tokenizer.json</code>. Common words are one token, rare words several, and any byte sequence at all can be encoded, so there is no "unknown" token. Qwen3 has a vocabulary of 151,936 entries; Qwen3.5 has 248,320.</p>
<p>A few tokens are <strong>special</strong>: they are never produced by splitting ordinary text, and they carry structure.</p>
<table>
<tr><th>Token</th><th>Id (Qwen3)</th><th>Meaning</th></tr>
<tr><td><code>&lt;|endoftext|&gt;</code></td><td>151643</td><td>end of a document in pretraining</td></tr>
<tr><td><code>&lt;|im_start|&gt;</code></td><td>151644</td><td>start of a chat turn</td></tr>
<tr><td><code>&lt;|im_end|&gt;</code></td><td>151645</td><td>end of a chat turn</td></tr>
<tr><td><code>&lt;think&gt;</code>, <code>&lt;/think&gt;</code></td><td>151667, 151668</td><td>wrap the model's reasoning</td></tr>
</table>
<p>You do not implement BPE yourself. The <code>Tokenizers</code> library from swift-transformers reads the same files as Python's <code>transformers</code> and produces identical ids. <code>AutoTokenizer.from(modelFolder:)</code> loads it from the checkpoint folder.</p>
"""),
        dict(title="The chat template", body="""
<p>A chat model was fine-tuned on conversations in one exact format, and it only behaves well if you reproduce that format to the byte. The format is stored with the model, in <code>tokenizer_config.json</code> (or <code>chat_template.jinja</code>), as a Jinja template. For Qwen it is <strong>ChatML</strong>. One user message renders as:</p>
""" + block('''<|im_start|>user
Why is the sky blue?<|im_end|>
<|im_start|>assistant
<think>

</think>

''', "text") + """
<p>The prompt ends at the start of the assistant's turn, and the model continues from there. The empty <code>&lt;think&gt;</code> block is what <code>enable_thinking: false</code> produces: Qwen3 and Qwen3.5 are hybrid reasoning models, and an already-closed think block tells them to answer directly. With thinking enabled, the template stops after <code>assistant\\n</code>, and the model writes its reasoning inside <code>&lt;think&gt;...&lt;/think&gt;</code> before the answer.</p>
<p>Our wrapper passes the messages, the tools (Lesson 21) and the thinking flag straight to the template engine:</p>
""" + source("Sources/Inference/LoadedModel.swift", "    /// Formats a conversation, and the tools", "    }") + """
<p>For the example above this produces the 18 ids <code>[151644, 872, 198, 10234, 374, 279, 12884, 6303, 30, 151645, 198, 151644, 77091, 198, 151667, 271, 151668, 271]</code>, the same ids Python's <code>apply_chat_template</code> produces. Comparing the two is the first test to write for any new model: a wrong template does not crash, it just makes the model quietly worse.</p>
"""),
        dict(title="When to stop", body="""
<p>Generation stops when the model emits an end token. Which one? <code>config.json</code> names one <code>eos_token_id</code>, but in practice a chat model ends a turn with <code>&lt;|im_end|&gt;</code>, a base model ends a document with <code>&lt;|endoftext|&gt;</code>, and a fine-tune sometimes uses either. The loader collects all of them into a set:</p>
""" + source("Sources/Inference/LoadedModel.swift", "        // Chat models end a turn with", "compactMap { $0 })") + """
<p>Checking membership in this set after every token is cheap, and stopping one token too late is far more visible to users (the model starts writing the next user turn) than any cost of the check.</p>
"""),
        dict(title="Streaming text from tokens", body="""
<p>Streaming means sending text after every token. The obvious approach, decoding each token on its own and sending the result, breaks in two ways:</p>
<ul>
<li><strong>Multi-byte characters.</strong> Byte-level BPE can split one character across tokens. An emoji is four UTF-8 bytes and may arrive as two tokens; decoding the first alone gives the replacement character U+FFFD (�).</li>
<li><strong>Context-dependent spacing.</strong> Some tokenizers decide how a token prints based on its neighbours, so decoding tokens one by one does not always concatenate to the decoding of the whole sequence.</li>
</ul>
<p>The fix is to decode a window of recent tokens, emit only the part of the text that is new, and wait if the text ends in U+FFFD:</p>
""" + source("Sources/Inference/Detokenizer.swift", "public struct StreamingDetokenizer") + """
<p>Decoding the whole output after every token would be correct but quadratic in length. Restarting the window after each newline keeps the work per token small, because a newline is a safe boundary for every tokenizer in this course.</p>
"""),
        dict(title="Stop strings", body="""
<p>Clients can ask generation to stop at strings such as <code>"\\n\\nUser:"</code>. The difficulty is the same as above, one level up: a stop string can arrive split over several tokens. If you stream <code>"\\n\\nUs"</code> and only then see <code>"er:"</code>, the client already has text it should never have received.</p>
<p>So the matcher holds back any suffix of the pending text that could still become a stop string, and releases it as soon as it cannot:</p>
""" + source("Sources/Inference/Detokenizer.swift", "public struct StopMatcher") + """
<p>The unit tests in <code>Tests/InferenceTests/TextTests.swift</code> pin both behaviours: <code>"hello E" + "N" + "D tail"</code> with stop <code>"END"</code> emits only <code>"hello "</code>, and <code>"an E" + "xit"</code> releases the held-back <code>"E"</code> once <code>"Ex"</code> rules out <code>"END"</code>. When generation ends for any other reason, the engine calls <code>finish()</code> to flush whatever was held back.</p>
"""),
    ],
    exercises=[
        dict(type="mcq", prompt="<p>Your server renders prompts with a hand-written template that differs from Qwen's by one newline. What happens?</p>",
             options=["Tokenization fails with an error",
                      "Nothing; models ignore whitespace",
                      "The model still runs, but answers get quietly worse because the input no longer matches its training format",
                      "The server returns HTTP 400"], answer=2,
             explain="<p>Nothing checks the format. The model sees an input slightly outside what it was tuned on and degrades without any error, which is why the template from the checkpoint should always be used.</p>"),
        dict(type="fill", prompt="<p>Which special token does a Qwen chat model emit to end its turn?</p>",
             answer=["<|im_end|>", "im_end", "|im_end|"], placeholder="token",
             explain="<p>ChatML closes every turn with <code>&lt;|im_end|&gt;</code>. <code>&lt;|endoftext|&gt;</code> ends a pretraining document and is kept in the stop set for base models.</p>"),
        dict(type="mcq", prompt="<p>The detokenizer decodes the window and gets text ending in U+FFFD. What should it do?</p>",
             options=["Send it; the client will fix it",
                      "Send nothing yet, because the last token ends in the middle of a multi-byte character",
                      "Drop the token",
                      "Restart the window"], answer=1,
             explain="<p>U+FFFD at the end means the bytes so far do not complete a character. The next token will, and the full character goes out then.</p>"),
        dict(type="mcq", prompt="<p>Stop string <code>\"STOP\"</code>. The stream so far is <code>\"ok ST\"</code>. What may be sent to the client right now?</p>",
             options=["\"ok ST\"", "\"ok \"", "nothing", "\"ok S\""], answer=1,
             explain="<p>\"ST\" is a prefix of \"STOP\", so it must be held back until the next text shows whether the stop string completes.</p>"),
        dict(type="mcq", prompt="<p>Why does the chat template append an empty <code>&lt;think&gt;\\n\\n&lt;/think&gt;</code> when thinking is disabled?</p>",
             options=["It is a bug in the template",
                      "It shows the model that the reasoning phase is already over, so it answers directly",
                      "It reserves cache space",
                      "It is required by the tokenizer"], answer=1,
             explain="<p>Hybrid reasoning models were trained to reason inside think tags. A closed, empty block is the trained signal for \"no reasoning, answer now\".</p>"),
    ],
))

# ------------------------------------------------------------------ 7
LESSONS.append(dict(
    part="Part II · Running Qwen",
    title="Implementing Qwen3",
    blurb="Write the whole Qwen3 decoder in about 150 lines: grouped-query attention with QK-norm and rotary positions, a SwiGLU MLP, pre-norm residual blocks, and a tied output head.",
    viz=False,
    goals=[
        "Trace the shapes through one Qwen3 attention layer",
        "Explain grouped-query attention and why it shrinks the KV cache",
        "Explain QK-norm and rotary position embeddings at the level the code needs",
        "Assemble blocks into a full model with a tied output projection",
    ],
    recap="Qwen3 is a stack of identical pre-norm blocks: x + attention(norm(x)), then h + mlp(norm(h)). Attention projects to 16 query heads and 8 shared key/value heads, normalizes queries and keys per head, rotates them by position, and runs fused causal attention against the cache. The MLP is SwiGLU. A final norm and the tied embedding matrix turn the last hidden state into logits.",
    sections=[
        dict(title="The shape of the model", body="""
<p>Qwen3-0.6B, which Lessons 7 to 10 use, has this structure:</p>
""" + block('''token ids [B, L]
  → embed_tokens                 [B, L, 1024]
  → 28 × TransformerBlock:
        h = x + Attention(RMSNorm(x))
        x = h + MLP(RMSNorm(h))
  → RMSNorm
  → embed_tokens.asLinear        [B, L, 151936]   (tied output head)
→ logits''', "text") + """
<p>Every block has the same code and different weights. Writing the model therefore means writing four small modules: attention, the MLP, the block that wires them with residual connections, and the outer model.</p>
"""),
        dict(title="Attention", body="""
""" + source("Sources/Inference/Qwen3.swift", "final class Attention") + """
<p>Follow the shapes for a batch of one, <code>L</code> tokens:</p>
<ol>
<li><strong>Project.</strong> <code>q_proj</code> maps 1024 to 16 heads × 128 = 2048; <code>k_proj</code> and <code>v_proj</code> map to 8 heads × 128 = 1024. Reshape to <code>[1, L, heads, 128]</code> and transpose to <code>[1, heads, L, 128]</code>, the layout the attention kernel wants.</li>
<li><strong>QK-norm.</strong> Each query and key vector is RMS-normalized with its own learned scale. This is new in Qwen3: it keeps attention scores in a stable range, which lets the model train at large learning rates without spikes. For us it is just one more <code>RMSNorm</code> over the last dimension, applied before RoPE.</li>
<li><strong>Rotary positions.</strong> RoPE rotates each pair of dimensions by an angle proportional to the token's position, at a different frequency per pair (base <code>rope_theta</code> = 1,000,000). The dot product of a rotated query and key then depends on the distance between them, which is how attention knows word order.</li>
<li><strong>Attend</strong> to everything cached so far, plus these tokens.</li>
<li><strong>Merge heads</strong> back to <code>[1, L, 2048]</code> and project to 1024 with <code>o_proj</code>.</li>
</ol>
<p>Steps 3 and 4 live in a small helper, <code>attend</code>, shared by both model families, because the cache logic is the same for all of them:</p>
""" + source("Sources/Inference/LayerCache.swift", "    let kv = cache as? KVCache", "        queries: rope(q, offset)", include_end=True) + """
<p>(The helper's first branch handles batches of independent sequences, Lesson 15.) The <code>offset</code> is the number of tokens already in the cache: during prefill it is 0, and when decoding token 600 it is 599, so that token is rotated to the right position. The mask is <code>.causal</code> when several tokens arrive at once, so token <em>i</em> cannot see tokens after it; a single decode token may see everything, so no mask is needed.</p>
"""),
        dict(title="Grouped-query attention", body="""
<p>There are 16 query heads but only 8 key/value heads. Each pair of query heads shares one key/value head. This is <strong>grouped-query attention</strong> (GQA), and its purpose is the cache: keys and values are what must be stored for every past token, so halving the KV heads halves the cache with little loss in quality. Larger Qwen3 models go further; the 32B model has 64 query heads and 8 KV heads.</p>
<p>The fused attention kernel handles the grouping itself when the number of query heads is a multiple of the KV heads, so the code never copies keys to match queries. Lesson 9 turns this into concrete megabytes.</p>
"""),
        dict(title="MLP and block", body="""
""" + source("Sources/Inference/Qwen3.swift", "let swiglu = compile") + source("Sources/Inference/Qwen3.swift", "final class MLP") + """
<p>SwiGLU uses two input projections: one is passed through SiLU and acts as a gate on the other, elementwise. Then <code>down_proj</code> maps the 3072-wide result back to 1024. The gate-times-value product is compiled into one kernel, as Lesson 4 described.</p>
""" + source("Sources/Inference/Qwen3.swift", "final class TransformerBlock") + """
<p>The block is <strong>pre-norm</strong>: each sublayer sees a normalized input, and its output is <em>added</em> to the residual stream rather than replacing it. The stream itself is never normalized inside the stack, which is why its values can grow large; in Qwen3-0.6B some reach about 8,000 by layer 2. Keep that in mind for the next lesson, because bfloat16 at 8,000 has a step size of 32.</p>
<p>The <code>mlp</code> property is typed <code>UnaryLayer</code> so that mixture-of-experts layers can take its place (Lesson 16).</p>
"""),
        dict(title="The full model", body="""
""" + source("Sources/Inference/Qwen3.swift", "final class Qwen3Backbone") + source("Sources/Inference/Qwen3.swift", "public final class Qwen3Model") + """
<p>The outer key <code>"model"</code> reproduces the checkpoint's <code>model.</code> prefix. <code>lm_head</code> is optional: for tied models the property stays <code>nil</code>, so the parameter tree has no <code>lm_head.weight</code>, which is exactly what <code>verify: [.all]</code> expects. <code>makeCaches</code> returns one empty cache per layer; Lesson 9 fills them.</p>
<p>The model conforms to a two-method protocol that the rest of the server programs against, so the generation loop and engines work for Qwen3 and Qwen3.5 alike:</p>
""" + source("Sources/Inference/LanguageModel.swift", "public protocol LanguageModel") + """
<p>That is the whole model. The next lesson loads real weights into it and proves it computes the same thing as the reference implementation.</p>
"""),
    ],
    exercises=[
        dict(type="numeric", prompt="<p>Qwen3-0.6B: hidden size 1024, 16 query heads, head dim 128. What is the output width of <code>q_proj</code>?</p>",
             answer=2048, tolerance=0, placeholder="width",
             explain="<p>16 heads × 128 = 2048. Note it is wider than the hidden size: Qwen3 sets head_dim independently of hidden_size / heads.</p>"),
        dict(type="mcq", prompt="<p>With 16 query heads and 8 KV heads, how does the KV cache compare with full multi-head attention (16 KV heads)?</p>",
             options=["Same size", "Half the size", "A quarter of the size", "Twice the size"], answer=1,
             explain="<p>The cache stores keys and values per KV head. Eight instead of sixteen halves it.</p>"),
        dict(type="mcq", prompt="<p>Decoding the 600th token, what offset does RoPE use?</p>",
             options=["0", "1", "599", "600"], answer=2,
             explain="<p>Positions count from 0. The cache holds 599 tokens (positions 0 to 598), so the new token is at position 599.</p>"),
        dict(type="mcq", prompt="<p>Why is no attention mask needed when decoding a single token?</p>",
             options=["Single tokens skip attention",
                      "The only token in the query is the newest, and it is allowed to see every cached token",
                      "The cache is already masked",
                      "Masks only matter for MoE"], answer=1,
             explain="<p>Causality forbids seeing the future. A lone query is the latest position, so nothing in the keys is in its future.</p>"),
        dict(type="order", prompt="<p>Order the steps inside Qwen3 attention.</p>",
             items=["Project to queries, keys and values", "RMS-normalize queries and keys per head",
                    "Rotate queries and keys by position (RoPE)", "Append keys and values to the cache",
                    "Fused causal attention", "Merge heads and apply o_proj"],
             explain="<p>QK-norm comes before RoPE in Qwen3; keys are rotated before caching, so cached keys never need rotating again.</p>"),
    ],
))

# ------------------------------------------------------------------ 8
LESSONS.append(dict(
    part="Part II · Running Qwen",
    title="Loading weights and proving parity",
    blurb="A model that loads and produces fluent text can still be wrong. Prove yours matches the reference, learn what agreement in bfloat16 actually looks like, and how to find the first layer that disagrees.",
    viz=False,
    goals=[
        "Set up a pinned Python reference to compare against",
        "Decide what counts as a match when both sides compute in bfloat16",
        "Bisect a mismatch down to the first layer and operation that differs",
        "Recognize a greedy-decoding near-tie and tell it apart from a bug",
    ],
    recap="Compare logits, not text. Pin the reference to the same MLX core version. In bfloat16, expect exact agreement for the first position and last-digit differences elsewhere, with the same top token everywhere. When logits differ more than that, compare layer by layer to find the first divergence. When greedy output diverges after many identical tokens, check whether the top two logits were within one bfloat16 step.",
    sections=[
        dict(title="Why text is not enough", body="""
<p>Get the RoPE base wrong, swap two projections, or forget QK-norm, and a 0.6B model often still writes grammatical English. It is just a slightly worse model, and you might not notice for weeks. The only reliable check is numerical: run the same input through your implementation and through a trusted one, and compare the <strong>logits</strong>, the raw scores for every vocabulary entry at every position.</p>
<p>The trusted implementation here is Python's <code>mlx-lm</code>, which runs on the same MLX core. Pin it to the same core version as the Swift package. <code>mlx-swift</code> 0.32.3 bundles MLX 0.32.2, so:</p>
""" + block('''uv venv ref && VIRTUAL_ENV=ref uv pip install "mlx==0.32.2" "mlx-metal==0.32.2" mlx-lm
ref/bin/python - <<'PY'
import mlx.core as mx
from mlx_lm import load
model, _ = load("mlx-community/Qwen3-0.6B-4bit")
ids = mx.array([[9707, 11, 1246, 525, 498, 30, 358, 1079]])   # same ids as infer's logits mode
mx.save_safetensors("python.safetensors", {"logits": model(ids).astype(mx.float32)})
PY''', "shell") + """
<p>On the Swift side, the <code>infer</code> tool has a mode that writes logits for a fixed prompt to a file:</p>
""" + source("Sources/infer/main.swift", 'if mode == "logits"') + """
<p>Then load both files in Python and compare position by position.</p>
"""),
        dict(title="What a match looks like", body="""
<p>The very first comparison made for this course, Qwen3-0.6B at 4 bits on the four tokens of <code>&lt;|im_start|&gt;user\nHello</code>, gave:</p>
""" + block('''position          0      1       2       3
max |Δ logit|     0      0.69    0.34    0.39      (logits reach about 16)
argmax agrees     yes    yes     yes     yes''', "text") + """
<p>Is that a pass? Position 0 is exact, every position picks the same top token, and the differences are a few bfloat16 steps. A logit near 16 has a bfloat16 step of 0.125, so 0.69 is about five steps. That is the signature of the same computation with operations rounded in a slightly different order somewhere, not of a wrong computation. A real bug looks very different: large differences from the first position on, or a different top token at most positions.</p>
<p>But "looks like rounding" is a hypothesis, and position 0 being exact is a useful clue: at position 0 a token attends only to itself, so whatever differs must involve mixing information across positions. That narrows the search to attention.</p>
"""),
        dict(title="Bisecting a difference", body="""
<p>The method is simple: dump the hidden state after every layer from both implementations, and find the first layer where they differ. A temporary debug function in Swift saved each layer's output; the Python side looped over <code>model.model.layers</code> the same way. The result:</p>
""" + block('''layer   max |Δ|    max |h|
0       0          7.4
1       0          12.6
2       0          7968       ← the residual stream gets large here
3       0          7968
4       0.0078     7968       ← first difference: one bf16 step, inside attention
5       0.031      7968
...
27      3.9        5120''', "text") + """
<p>Layers 0 to 3 are bit-identical. The first difference is one bfloat16 step in layer 4's attention output at a single position, and from there it spreads and grows, because each layer adds to the residual stream and a value of 8,000 has a bfloat16 step of 32. By layer 27 the absolute difference is 3.9, which is still smaller than one step at that magnitude.</p>
<p>Zooming in further, each of the fast kernels involved (RoPE and fused attention) was run alone on the same inputs in Swift and Python, and matched bit for bit. Fusing <code>silu(gate) * up</code> to match Python's compiled <code>swiglu</code> changed nothing. So the remaining difference is below the level of our code: the same Metal source, compiled by a different Metal compiler for the Swift build than for the Python wheel, can round one value differently on particular inputs. You can stop here. The implementation is correct, and you now know the tolerance to expect.</p>
<div class="note"><p class="text-sm"><strong>The general lesson.</strong> Treat "matches to the last digit" as unattainable across builds, and "same top token everywhere, differences of a few steps at the logit's magnitude, exact where no cross-position mixing happens" as the pass condition. Then test it on more than one prompt.</p></div>
"""),
        dict(title="Greedy near-ties", body="""
<p>The other comparison is end-to-end: generate 200 tokens greedily (always the top token) in both implementations. With the prompt "Why is the sky blue?", the first 35 tokens are identical, then they part ways. Is that a bug?</p>
<p>Check the logits at the divergence point:</p>
""" + block('''top candidates at token 35:   " all" 21.875    " a" 21.75    " various" 21.75
Python chose " all"; Swift chose " a"''', "text") + """
<p>The top two are 0.125 apart, exactly one bfloat16 step at that magnitude. A one-step difference anywhere upstream is enough to flip that choice, and after the flip the two texts continue from different prefixes, so they diverge completely. This is expected behaviour, and you will see it again in Lesson 15 (batched decoding) and Lesson 19 (speculative decoding), where a different kernel shape changes the rounding. The test is always the same: at the first divergent token, are the top two logits within a step or two? If yes, it is a near-tie; if no, it is a bug.</p>
"""),
        dict(title="Turn it into tests", body="""
<p>Comparisons against Python are a development tool; you do not want Python in your test suite. What you can keep is <strong>self-consistency</strong> tests that encode the same tolerance. For example, decoding several prompts as one batch must match decoding each alone:</p>
""" + source("Tests/InferenceTests/BatchTests.swift", "func batchedDecodeMatchesSerial", "    // Batched: prefill", include_end=False) + """
<p>The full test then decodes the same prompts in a batch and requires every logit to be within 1.0 of the serial run, for both Qwen3 and Qwen3.5. It runs in about 8 seconds. The model-backed tests look for the checkpoints in the Hugging Face cache, or in paths given by environment variables, and fail with a clear message if the weights are missing.</p>
<p>The same method checked every architecture in this course against the reference before any lesson was written: Qwen3 (above), Qwen3.5 (same top token at every position, differences up to 0.58 at logits around 23), and the mixture-of-experts variants in Lesson 16.</p>
"""),
    ],
    exercises=[
        dict(type="numeric", prompt="<p>bfloat16 has 8 bits of precision (7 stored plus 1 implicit). What is the gap between adjacent bfloat16 values just above 16? (Hint: between 16 and 32 there are 128 values.)</p>",
             answer=0.125, tolerance=0.0001, placeholder="step",
             explain="<p>16 / 128 = 0.125. Between 2<sup>n</sup> and 2<sup>n+1</sup> there are 128 evenly spaced values, so the step is 2<sup>n</sup> / 128.</p>"),
        dict(type="mcq", prompt="<p>Your logits match exactly at position 0 and differ by a few bfloat16 steps elsewhere, with the same argmax everywhere. Where would a real bug most likely be, if there is one?</p>",
             options=["The embedding table", "The final norm",
                      "Something that mixes positions, such as attention or RoPE",
                      "The tokenizer"], answer=2,
             explain="<p>Position 0 attends only to itself and RoPE at position 0 is the identity. Everything per-position is therefore verified; only cross-position computation is left.</p>"),
        dict(type="mcq", prompt="<p>Greedy outputs are identical for 120 tokens and then diverge. At the divergence, the reference's top two logits are 18.50 and 12.25. What does this suggest?</p>",
             options=["A near-tie; nothing to worry about",
                      "A genuine bug: a 6-point gap cannot flip through rounding",
                      "The tokenizer differs",
                      "The sampler is random"], answer=1,
             explain="<p>Rounding moves logits by a step or two (0.0625 to 0.125 here). A gap of 6.25 means the two implementations computed materially different things at that point, for example a cache or position bug that only appears at long context.</p>"),
        dict(type="mcq", prompt="<p>Why pin the Python reference to the same MLX core version as the Swift package?</p>",
             options=["Different versions cannot load the same checkpoint",
                      "Kernel changes between versions can shift numbers by a few steps, which would hide or mimic real differences",
                      "Newer versions are slower",
                      "mlx-lm requires it"], answer=1,
             explain="<p>You want the comparison to isolate your code. Version drift adds its own small differences.</p>"),
    ],
))

# ------------------------------------------------------------------ 9
LESSONS.append(dict(
    part="Part II · Running Qwen",
    title="The generation loop and the KV cache",
    blurb="Turn a model into a token stream: prefill the prompt in chunks, keep every past key and value in a cache that grows in steps, and overlap CPU and GPU work so the GPU never waits.",
    viz=True,
    goals=[
        "Explain why caching keys and values turns decode from quadratic into linear work",
        "Compute KV cache memory for a model and context length",
        "Implement a cache that appends without copying the whole history every token",
        "Write a generation loop with chunked prefill and pipelined decode",
    ],
    recap="Without a cache, every new token would recompute keys and values for the entire history. The KV cache stores them once per token per layer, at a cost of 2 × kv_heads × head_dim × bytes per layer per token. The generator prefills the prompt in chunks, then repeatedly runs one token, samples, and feeds the sample back, queueing step n+1 on the GPU before handing token n to the caller.",
    sections=[
        dict(title="Prefill and decode", body="""
<p>Lesson 1 named the two phases. Now look at what the model computes in each. Attention at position <em>t</em> needs the keys and values of every position up to <em>t</em>. Those depend only on earlier tokens, which never change. So instead of recomputing them for every new token, store them:</p>
<ul>
<li><strong>Prefill</strong> runs the model on the whole prompt at once. Each attention layer computes keys and values for all prompt positions and stores them in its cache. The logits at the last position give the first generated token.</li>
<li><strong>Decode</strong> runs the model on one token. Each layer computes that token's key and value, appends them to the cache, and attends to the whole cache.</li>
</ul>
<p>Without the cache, generating <em>n</em> tokens would cost work proportional to 1 + 2 + … + <em>n</em>, which grows as <em>n</em>². With it, each step does one token's worth of projections plus an attention read over the cache.</p>
"""),
        dict(title="How big the cache gets", body="""
<p>Per token, each attention layer stores one key and one value vector per KV head:</p>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-sm text-ink-100">bytes per token = layers × 2 × kv_heads × head_dim × bytes per value</p>
<p>For Qwen3-0.6B in bfloat16: 28 × 2 × 8 × 128 × 2 = 114,688 bytes, about 112 KB per token. A 32,000-token context then needs 3.5 GB, roughly ten times the 4-bit weights. On long contexts the cache, not the model, decides how many requests fit in memory, and reading it is part of every decode step's memory traffic.</p>
<p>Qwen3.5 changes this picture dramatically. Only 6 of its 24 layers keep a KV cache, with 2 KV heads each; the other 18 keep a fixed-size state instead (Lesson 17). Try both models below.</p>
""", figure=fig("viz-kvcache", "Cache memory versus context length",
                "Drag the context length. Qwen3.5 keeps a KV cache in only a quarter of its layers, plus a fixed recurrent state.")),
        dict(title="A cache that grows in steps", body="""
""" + source("Sources/Inference/KVCache.swift", "public final class KVCache") + """
<p>The naive cache concatenates new keys onto old ones every step. That copies the whole history every token, which is quadratic again, just with a smaller constant. This cache allocates room for 256 positions at a time and writes each new token into the next free slot. Only when the buffer is full does it allocate the next block and copy. <code>update</code> returns a view of the filled part, which is what attention reads.</p>
<p><code>trim</code> moves the write position back without touching memory. Speculative decoding (Lesson 19) uses it to forget draft tokens the model rejected, and it is why a cache that "forgets" can be nearly free.</p>
"""),
        dict(title="The generator", body="""
""" + source("Sources/Inference/Generator.swift", "public struct TokenGenerator") + """
<p>Read it in three parts.</p>
<p><strong>Chunked prefill.</strong> The prompt, except its last token, is run in chunks of 512. Chunking bounds the memory of one forward pass, since attention scores for a chunk scale with chunk × cache length. Each chunk's caches are evaluated immediately so the lazy graph does not grow across chunks. The last prompt token goes through the regular step, because it is the one whose logits matter.</p>
<p><strong>Pipelined decode.</strong> In <code>next()</code>, the generator builds and <code>asyncEval</code>s the forward pass for the <em>next</em> token before calling <code>item()</code> on the current one. While the caller detokenizes and streams the current token, the GPU is already computing the next. On the M1 this takes decode from 12.15 to 10.9 ms per token, an 11% gain for four lines of code.</p>
<p><strong>Bookkeeping.</strong> <code>fed</code> records every token that has gone into the model, so it always says exactly which positions the caches hold, including the look-ahead token. <code>checkpoint</code> copies the caches at a chosen prompt position. Both exist for the prompt cache in Lesson 14; ignore them for now.</p>
"""),
        dict(title="Running it", body="""
<p>With the sampler from the next lesson, this is the core of the <code>infer</code> tool: format a prompt, iterate the generator, stop at an end token, and stream text through the detokenizer.</p>
""" + block('''let model = try loadQwen3(from: directory)
let tokenizer = try await AutoTokenizer.from(modelFolder: directory)
let prompt = try tokenizer.applyChatTemplate(
    messages: [["role": "user", "content": "Why is the sky blue?"]], tools: nil,
    additionalContext: ["enable_thinking": false])

var detokenizer = StreamingDetokenizer(tokenizer: tokenizer)
for token in TokenGenerator(model: model, prompt: prompt, parameters: .init(), maxTokens: 200) {
    if token == 151645 { break }               // <|im_end|>
    print(detokenizer.append(token), terminator: "")
}''', "swift") + """
<p>On a base M1 with Qwen3-0.6B at 4 bits this streams at about 60 tokens per second in a Debug build. Remember Lesson 3: measure in Release.</p>
"""),
    ],
    exercises=[
        dict(type="numeric", prompt="<p>A model has 32 layers, 8 KV heads, head dim 128, and caches in bfloat16. How many kilobytes per token does its KV cache use? (1 KB = 1024 bytes.)</p>",
             answer=128, tolerance=0.5, placeholder="KB",
             explain="<p>32 × 2 × 8 × 128 × 2 = 131,072 bytes = 128 KB per token.</p>"),
        dict(type="numeric", prompt="<p>Same model, 16,000-token context. About how many gigabytes is the cache? (1 GB = 2<sup>30</sup> bytes; one decimal.)</p>",
             answer=2.0, tolerance=0.06, placeholder="GB",
             explain="<p>131,072 × 16,000 = 2.10 × 10<sup>9</sup> bytes ≈ 1.95 GB, so about 2.0 GB.</p>"),
        dict(type="mcq", prompt="<p>Why does the cache grow in blocks of 256 positions instead of concatenating each new token?</p>",
             options=["To save memory",
                      "Concatenating copies the whole history every token, which makes decode quadratic again",
                      "MLX cannot concatenate",
                      "Attention requires multiples of 256"], answer=1,
             explain="<p>Writing into preallocated space costs one token's worth of work; reallocating happens once per 256 tokens.</p>"),
        dict(type="mcq", prompt="<p>Why is the last prompt token not part of the prefill chunks?</p>",
             options=["It is the end token",
                      "Its logits are needed to sample the first output token, so it goes through the regular step",
                      "It does not fit in a chunk",
                      "RoPE cannot handle it"], answer=1,
             explain="<p>Prefill chunks only need to fill the cache, so their logits are thrown away. The last position's logits produce the first token.</p>"),
        dict(type="mcq", prompt="<p>What does the generator overlap by calling asyncEval on step n+1 before item() on step n?</p>",
             options=["Two GPU kernels",
                      "CPU work for token n (reading, detokenizing, streaming, building the next graph) with GPU work for token n+1",
                      "Prefill and decode",
                      "Two requests"], answer=1,
             explain="<p>Without it, the GPU idles while the CPU handles each token. With it, the next forward pass is already running.</p>"),
    ],
))

# ------------------------------------------------------------------ 10
LESSONS.append(dict(
    part="Part II · Running Qwen",
    title="Sampling",
    blurb="Logits are scores, not choices. Implement greedy decoding, temperature, top-k, top-p and min-p on the GPU, with reproducible seeds, and learn what each knob does to the distribution.",
    viz=True,
    goals=[
        "Turn logits into a probability distribution with temperature",
        "Implement top-k, top-p and min-p truncation with MLX operations",
        "Make sampling reproducible with explicit random keys",
        "Explain why the sampler exposes its filtered distribution",
    ],
    recap="Temperature divides the logits before the softmax: below 1 sharpens, above 1 flattens, 0 means greedy. Top-k keeps the k best tokens, top-p the smallest set whose probability reaches p, min-p every token at least p times as likely as the best one. All three work on log-probabilities on the GPU, and the result is renormalized before drawing from it. A split random key makes the whole sequence reproducible.",
    sections=[
        dict(title="From logits to a distribution", body="""
<p>The model's output for the last position is 151,936 logits. Softmax turns them into probabilities. Before the softmax, divide by a <strong>temperature</strong> <code>T</code>:</p>
<ul>
<li><code>T = 1</code>: the model's own distribution.</li>
<li><code>T &lt; 1</code>: differences are magnified, so likely tokens become more likely. Answers get more focused and more repetitive.</li>
<li><code>T &gt; 1</code>: the distribution flattens, so unlikely tokens get a real chance. Answers get more varied and less coherent.</li>
<li><code>T → 0</code>: all mass goes to the top token. That is <strong>greedy</strong> decoding, which we special-case as a plain argmax.</li>
</ul>
<p>Temperature alone has a problem: the tail. With 150,000 tokens, even tiny probabilities add up to a noticeable chance of drawing nonsense. The truncation methods cut the tail off before drawing.</p>
"""),
        dict(title="Truncation: top-k, top-p, min-p", body="""
<table>
<tr><th>Method</th><th>Keeps</th><th>Behaviour</th></tr>
<tr><td>top-k</td><td>the k most likely tokens</td><td>Fixed size. Too few when many tokens are plausible, too many when one is obvious.</td></tr>
<tr><td>top-p (nucleus)</td><td>the smallest set of most likely tokens whose total probability reaches p</td><td>Adapts: a few tokens when the model is confident, many when it is not.</td></tr>
<tr><td>min-p</td><td>tokens with probability at least p × the top token's probability</td><td>Adapts to confidence directly; cheap, because it needs no sort.</td></tr>
</table>
<p>Try them below on a toy distribution. Notice that min-p and top-p both shrink the kept set when the distribution is peaked (low temperature) and grow it when it is flat, while top-k does not care.</p>
""", figure=fig("viz-sampling", "Sampling controls",
                "Adjust temperature and truncation. Faded bars are cut; the rest are renormalized before drawing.")),
        dict(title="The sampler", body="""
""" + source("Sources/Inference/Sampler.swift", "public struct SamplingParameters") + source("Sources/Inference/Sampler.swift", "public func logProbabilities") + """
<p>Everything runs on log-probabilities, on the GPU, without leaving MLX:</p>
<ul>
<li><strong>Temperature</strong> scales the logits, and subtracting <code>logSumExp</code> turns them into log-probabilities without overflow.</li>
<li><strong>Top-k</strong> uses <code>argPartition</code>, which puts the k-th largest element in its sorted position without sorting the whole vocabulary, and masks everything below it to −∞.</li>
<li><strong>Min-p</strong> is one comparison: in log space, "at least p times the top probability" is "at least max + log p".</li>
<li><strong>Top-p</strong> needs a sort: sort descending, take the cumulative sum of probabilities, keep each token whose preceding mass is still below p (so the token that crosses p is kept), and scatter the mask back to vocabulary order with <code>putAlong</code>.</li>
<li>The survivors are <strong>renormalized</strong> so they sum to 1 again.</li>
</ul>
<p>Why return the distribution instead of just a token? Speculative decoding (Lesson 18) must know the exact probability the sampler would give each token, both for the target model and for the drafter. Exposing <code>logProbabilities</code> makes the sampler's distribution a value the rest of the code can reason about.</p>
"""),
        dict(title="Drawing, reproducibly", body="""
""" + source("Sources/Inference/Sampler.swift", "public mutating func callAsFunction") + source("Sources/Inference/Sampler.swift", "public mutating func sample(fromLogProbs") + """
<p><code>categorical</code> draws an index with probability proportional to <code>exp(logprob)</code>, and −∞ entries can never be drawn. When a request sets <code>seed</code>, the sampler keeps an explicit random key and splits it before every draw: one half becomes the new key, the other is used once. The sequence of draws then depends only on the seed, not on whatever else used the global random state, so the same request with the same seed returns the same text. Without a seed, MLX's global generator is used.</p>
<p>Two practical notes. Greedy decoding skips all of this and calls <code>argMax</code>, which is both faster and exactly reproducible. And OpenAI's API defaults to temperature 1; the server in this course defaults to 0.7, a common choice for chat with small models.</p>
"""),
    ],
    exercises=[
        dict(type="mcq", prompt="<p>What does temperature 0.5 do compared with 1.0?</p>",
             options=["Halves every probability",
                      "Doubles every logit before the softmax, sharpening the distribution toward the top tokens",
                      "Keeps only half the tokens",
                      "Has no effect on greedy decoding only"], answer=1,
             explain="<p>Dividing logits by 0.5 doubles them, which magnifies their differences after the softmax.</p>"),
        dict(type="numeric", prompt="<p>Probabilities in descending order: 0.50, 0.20, 0.15, 0.10, 0.05. How many tokens does top-p = 0.8 keep?</p>",
             answer=3, tolerance=0, placeholder="tokens",
             explain="<p>Mass before each token: 0, 0.50, 0.70, 0.85, ... A token is kept while the mass before it is below 0.8: the first three (0.50 + 0.20 + 0.15 = 0.85 ≥ 0.8).</p>"),
        dict(type="numeric", prompt="<p>Same probabilities. How many tokens does min-p = 0.25 keep?</p>",
             answer=3, tolerance=0, placeholder="tokens",
             explain="<p>Threshold = 0.25 × 0.50 = 0.125. Tokens at or above it: 0.50, 0.20, 0.15. Three.</p>"),
        dict(type="mcq", prompt="<p>Why does the top-k code use argPartition instead of argSort?</p>",
             options=["argSort does not exist in MLX",
                      "It only needs the k-th largest value, which partitioning finds without sorting all 150,000 entries",
                      "argPartition is more accurate",
                      "To support batches"], answer=1,
             explain="<p>Partitioning is linear time; a full sort is not, and the order of the kept tokens does not matter.</p>"),
        dict(type="mcq", prompt="<p>Two requests with the same prompt, temperature 0.8 and seed 42 return different text. Which is the likely cause in a server built like this one?</p>",
             options=["Seeds do not work in MLX",
                      "Something else differs, e.g. one request hit the prompt cache or ran in a batch and got slightly different logits, flipping a near-tie",
                      "Temperature ignores seeds",
                      "The tokenizer is random"], answer=1,
             explain="<p>The random draws are reproducible, but they are applied to logits. Any change in how the logits were computed (a different kernel shape, a different cache path) can move a token across a sampling boundary.</p>"),
    ],
))
