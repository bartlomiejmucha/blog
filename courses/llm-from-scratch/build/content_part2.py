# -*- coding: utf-8 -*-
"""Part II continued — lessons 6-10."""
from content_part1 import fig

LESSONS = []

# ------------------------------------------------------------------ 6
LESSONS.append(dict(
    part="Part II · The transformer",
    title="Multi-head attention",
    blurb="One attention head can only average one way. Running many in parallel, each in its own small subspace, lets a layer track several relationships at once.",
    viz=True,
    goals=[
        "Explain why a single attention head is a bottleneck",
        "Compute head dimensions from d_model and head count",
        "Describe how head outputs are recombined",
        "Explain MQA and GQA and why they exist",
    ],
    recap="Multi-head attention splits d_model into h independent subspaces, runs attention in each, concatenates the results and passes them through an output projection. Different heads specialise. GQA and MQA shrink the K/V projections to make the inference cache affordable.",
    sections=[
        dict(title="One head is one opinion", body="""
<p>A single attention head produces, per position, one set of weights summing to 1 — one weighted average. But a token in a real sentence needs several things at once. In <em>"The keys to the cabinet are on the table"</em>, the position of <code>are</code> needs the subject <code>keys</code> for agreement, and separately the syntactic structure, and separately the topic. One averaging operation cannot deliver all of that without blurring them into mush.</p>
<p>The fix is straightforward: run several heads in parallel, each with its own <code>W_Q</code>, <code>W_K</code>, <code>W_V</code>, so each learns to attend on a different criterion.</p>
"""),
        dict(title="The dimension arithmetic", body="""
<p>Crucially, the heads do <strong>not</strong> each get the full width. <code>d_model</code> is divided among them:</p>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-sm text-ink-100">d_head = d_model / n_heads</p>
<p>With <code>d_model = 4096</code> and 32 heads, each head works in 128 dimensions. Its Q, K and V projections are <code>[128, 4096]</code>, and it produces a 128-dimensional output per position. In code you will rarely see those 32 small matrices: implementations fuse them into one <code>[4096, 4096]</code> projection and slice the result into heads afterwards, which is the form the calculator below prints.</p>
<p>Then:</p>
<ol>
  <li>Concatenate all 32 head outputs → back to 4096 dimensions.</li>
  <li>Multiply by an output projection <code>W_O</code> of shape <code>[4096, 4096]</code>, which lets the heads' results mix and be rescaled before rejoining the residual stream.</li>
</ol>
<p>The total compute is about the same as one full-width head, which is the elegant part: you get many relationship types for free, paid for by giving each less room. That trade-off has a limit — heads that are too narrow cannot represent anything useful — which is why head count scales with model width rather than growing indefinitely.</p>
""", figure=fig("viz-heads", "Splitting d_model across heads",
                "Set d_model and head count to see the per-head shapes and parameter counts.")),
        dict(title="What individual heads learn", body="""
<p>Heads are not assigned roles; specialisation emerges from training. Interpretability work has identified recurring types:</p>
<ul>
  <li><strong>Positional heads</strong> — attend to the previous token, or to a fixed offset.</li>
  <li><strong>Syntactic heads</strong> — verbs attending to their subjects, adjectives to their nouns, closing brackets to their opening partners.</li>
  <li><strong>Coreference heads</strong> — pronouns attending to the entity they refer to.</li>
  <li><strong>Induction heads</strong> — the copy-the-pattern behaviour introduced in Lesson 5. These reliably appear during training at the same moment as a sharp jump in in-context learning ability.</li>
  <li><strong>Duplicate-token heads, name-mover heads</strong>, and other narrow circuits found by tracing specific tasks.</li>
</ul>
<p>Study the per-head patterns below on the same sentence and notice how different the same layer's heads look.</p>
""", figure=fig("viz-head-patterns", "Four heads, one sentence",
                "Each panel is a different simulated head on the same sentence. Hover any cell to see which pair it scores.")),
        dict(title="MQA and GQA: the inference-time fix", body="""
<p>At generation time you cache the keys and values of every past token so you do not recompute them (Lesson 11). That cache is proportional to <code>n_heads × d_head × n_layers × sequence_length</code>, and it becomes the dominant memory cost of serving a model with long context.</p>
<p>Two variants attack it:</p>
<ul>
  <li><strong>Multi-query attention (MQA)</strong> — keep all the query heads, but use a <em>single</em> shared key head and value head. The cache shrinks by a factor of <code>n_heads</code>. Quality degrades a little.</li>
  <li><strong>Grouped-query attention (GQA)</strong> — the middle ground now used almost everywhere. Group the query heads (say 32 queries into 8 groups); each group shares one key/value pair. A 4× or 8× cache reduction with quality close to full multi-head.</li>
</ul>
<p>This is a good example of a pattern you will see repeatedly: an architecture choice driven not by accuracy but by what it costs to <em>serve</em> the model.</p>
"""),
    ],
    exercises=[
        dict(type="numeric",
             prompt="<p>A model has <code>d_model = 2048</code> and 16 attention heads. What is <code>d_head</code>?</p>",
             answer="128", tolerance=0,
             placeholder="a whole number",
             explain="2048 / 16 = 128. Each head attends inside its own 128-dimensional subspace, and the 16 outputs concatenate back to 2048."),
        dict(type="mcq",
             prompt="<p>What is the main reason for using many heads rather than one wide head?</p>",
             options=["It reduces the total number of parameters",
                      "One head produces a single weighted average, so it can only track one relationship per position",
                      "It removes the need for the causal mask",
                      "Wide heads cannot be parallelised on a GPU"],
             answer="1",
             explain="It is about representational capacity, not cost — total compute is roughly unchanged. Multiple heads let one layer attend on several independent criteria simultaneously."),
        dict(type="mcq",
             prompt="<p>Grouped-query attention shares key and value projections across groups of query heads. What problem does that primarily solve?</p>",
             options=["Training instability in deep models",
                      "The size of the KV cache during inference",
                      "The quadratic cost of the attention score matrix",
                      "Tokenizer mismatch across languages"],
             answer="1",
             explain="GQA is an inference-memory optimisation. The QKᵀ matrix is still quadratic in sequence length — GQA does nothing about that; it shrinks what you must store per past token."),
        dict(type="multi",
             prompt="<p>Which are documented specialisations that emerge in attention heads? Select all.</p>",
             options=["Heads that attend from a pronoun to its antecedent",
                      "Heads that match a closing bracket to its opening bracket",
                      "Heads explicitly programmed by engineers to handle dates",
                      "Induction heads that copy a continuation seen earlier in the context"],
             answer=[0, 1, 3],
             explain="Nothing is hand-programmed. Every one of these roles is discovered by the model during training and only identified afterwards by interpretability researchers."),
        dict(type="numeric",
             prompt="<p>A layer with <code>d_model = 4096</code> uses 32 query heads and GQA with 8 key/value groups. How many key <em>heads</em> are stored per layer?</p>",
             answer="8", tolerance=0,
             placeholder="a whole number",
             explain="One key head per group, so 8 — a 4× reduction versus full multi-head, and therefore a 4× smaller KV cache."),
    ],
))

# ------------------------------------------------------------------ 7
LESSONS.append(dict(
    part="Part II · The transformer",
    title="Position: how the model knows word order",
    blurb="Attention is order-blind by construction. Something has to tell the model that 'dog bites man' differs from 'man bites dog'.",
    viz=True,
    goals=[
        "Explain why self-attention is permutation-equivariant",
        "Compare absolute, learned, and rotary position encodings",
        "Describe how RoPE encodes relative distance through rotation",
        "Explain why context-length extension is hard and how it is done",
    ],
    recap="Attention treats its input as a set. Position must be injected explicitly — historically by adding sinusoidal or learned vectors, now almost always by rotating query and key vectors by an angle proportional to position (RoPE), which makes attention scores depend on relative distance.",
    sections=[
        dict(title="The set problem", body="""
<p>Look again at the attention equation. Scores are dot products between queries and keys; the output is a weighted sum. Shuffle the input positions and every score simply moves with them — the computed values are identical. Self-attention treats its input as an unordered <strong>set</strong>.</p>
<p>That is a genuine problem, since word order carries a great deal of meaning. It is also a genuine feature: it is exactly what allows all positions to be processed in parallel, which is why transformers train so much faster than recurrent networks. The transformer's answer is not to restore sequential processing but to <strong>put position information into the vectors themselves</strong>.</p>
"""),
        dict(title="Approach 1: add a position vector", body="""
<p>The original 2017 transformer added a fixed sinusoidal vector to each token embedding. Dimension pairs oscillate at geometrically spaced frequencies:</p>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-xs text-ink-100">PE(pos, 2i) = sin(pos / 10000^(2i/d)) &nbsp;&nbsp; PE(pos, 2i+1) = cos(pos / 10000^(2i/d))</p>
<p>Fast dimensions distinguish neighbouring positions; slow ones distinguish far-apart regions. Together they give every position a unique fingerprint, a bit like the digits of a binary counter running at different rates.</p>
<p>GPT-2 and BERT instead used <strong>learned</strong> absolute embeddings: one trainable vector per position. Simple and effective, with one fatal limitation — position 4000 has no vector at all if you only trained up to 2048. The model cannot extrapolate one step beyond its training length.</p>
""", figure=fig("viz-sinusoid", "Sinusoidal position encoding",
                "Each row is a position, each column a dimension. Notice the frequency gradient left to right.")),
        dict(title="Approach 2: rotate the vectors (RoPE)", body="""
<p>Rotary position embedding is what essentially every current model uses, and the idea is neat.</p>
<p>Take the query and key vectors, split them into 2-dimensional pairs, and <strong>rotate each pair by an angle proportional to the position</strong>. Different pairs rotate at different rates, again geometrically spaced — pair <code>i</code> turns by <code>pos / 10000^(2i/d)</code> radians, the same base as the sinusoidal formula above. The first pairs complete a full turn every few tokens; the last ones barely move across the whole context. That spread is what the interpolation methods below act on: stretching the slow pairs buys range, and leaving the fast ones alone keeps neighbouring positions distinguishable.</p>
<p>The payoff is in what happens to the dot product. Rotating two vectors by angles <code>mθ</code> and <code>nθ</code> makes their dot product depend only on the difference <code>(m − n)</code>. So the attention score between two positions automatically encodes <strong>how far apart they are</strong>, not where they sit absolutely. The same phrase gets the same internal relationships whether it appears at position 10 or position 10,000.</p>
<p>Other properties that matter in practice:</p>
<ul>
  <li>It is applied to Q and K inside every attention layer, not added once at the bottom.</li>
  <li>It touches no parameters — it is a fixed geometric transform.</li>
  <li>Attention naturally decays with distance, which is a sensible prior for language.</li>
  <li>Because the encoding is relative and continuous, you can stretch it after training to extend context.</li>
</ul>
""", figure=fig("viz-rope", "RoPE as rotation",
                "Watch a query/key pair rotate with position and see how the dot product tracks their separation.")),
        dict(title="Stretching the context window", body="""
<p>A model trained on 8k tokens does not simply work at 128k. The rotation angles at position 100,000 are outside anything it saw, and quality collapses. The common techniques:</p>
<ul>
  <li><strong>Position interpolation</strong> — scale positions down so that 32k tokens occupy the angle range the model was trained on. Positions become fractional. Cheap, and works with a short fine-tune, but it compresses local resolution.</li>
  <li><strong>NTK-aware scaling / YaRN</strong> — scale the frequency bands unevenly: leave high-frequency (local) dimensions alone and stretch the low-frequency (global) ones. Preserves local precision much better.</li>
  <li><strong>Long-context fine-tuning</strong> — after any of the above, train on genuinely long documents so the model learns to use the range.</li>
</ul>
<div class="note note-warn"><p class="text-sm"><strong>Advertised context ≠ usable context.</strong> A model can accept 200k tokens and still retrieve poorly from the middle of them. The well-documented "lost in the middle" effect shows retrieval accuracy dipping for material in the middle of a long context relative to the beginning and end. Always measure on your own task rather than trusting the headline number.</p></div>
"""),
    ],
    exercises=[
        dict(type="mcq",
             prompt="<p>Why does a transformer need explicit position information at all?</p>",
             options=["Because the softmax cannot handle long sequences",
                      "Because self-attention computes the same result under any permutation of its inputs",
                      "Because the tokenizer discards word order",
                      "Because the residual stream overwrites earlier tokens"],
             answer="1",
             explain="Attention is permutation-equivariant — it sees a set. That property is what makes full parallelism possible, and position encoding is the price paid for it."),
        dict(type="mcq",
             prompt="<p>What is the key property of RoPE that absolute learned embeddings lack?</p>",
             options=["It uses fewer parameters at the embedding layer",
                      "Attention scores end up depending on the relative distance between positions rather than absolute indices",
                      "It removes the need for a causal mask",
                      "It lets the model attend to future tokens"],
             answer="1",
             explain="Rotating queries and keys by position-proportional angles makes their dot product a function of the difference of positions. Relative encoding generalises across the sequence in a way absolute indices do not."),
        dict(type="multi",
             prompt="<p>Which are true about extending a model's context window? Select all.</p>",
             options=["Position interpolation squeezes longer sequences into the trained angle range",
                      "A model can always be run at any length with no adaptation because RoPE is parameter-free",
                      "YaRN-style methods scale different frequency bands differently to preserve local detail",
                      "Retrieval accuracy can be worse for content in the middle of a long context"],
             answer=[0, 2, 3],
             explain="Parameter-free does not mean length-agnostic: the model has only ever seen a limited range of rotation angles, and quality falls apart outside it without interpolation plus fine-tuning."),
        dict(type="fill",
             prompt="<p>What is the abbreviation for the position encoding scheme that rotates query and key vectors by an angle proportional to position?</p>",
             answer=["rope", "rotary position embedding", "rotary positional embedding", "rotary"],
             placeholder="four letters",
             explain="RoPE — rotary position embedding. Introduced in the RoFormer paper and now near-universal in decoder-only LLMs."),
        dict(type="mcq",
             prompt="<p>A model was trained with learned absolute position embeddings up to 2048 tokens. You feed it 3000 tokens. What happens?</p>",
             options=["It works but more slowly",
                      "Positions beyond 2048 have no trained embedding, so behaviour there is undefined and output degrades badly",
                      "The tokenizer truncates automatically to 2048",
                      "The extra positions are handled by the causal mask"],
             answer="1",
             explain="There is literally no row in the position table for index 2048 and beyond. This inability to extrapolate is a large part of why the field moved to relative schemes like RoPE."),
    ],
))

# ------------------------------------------------------------------ 8
LESSONS.append(dict(
    part="Part II · The transformer",
    title="The transformer block",
    blurb="Attention plus a feed-forward network, wrapped in residual connections and normalisation. This unit, repeated dozens of times, is the entire model.",
    viz=True,
    goals=[
        "Draw a transformer block from memory, in the correct order",
        "Explain what residual connections do for gradients and for representation",
        "Explain LayerNorm and RMSNorm and why pre-norm won",
        "Describe the residual stream as a shared communication channel",
    ],
    recap="A block is: normalise, attend, add back; normalise, feed forward, add back. The residual stream carries information straight through; each sub-layer reads it, computes something, and adds a correction. Pre-norm placement is what makes very deep stacks trainable.",
    sections=[
        dict(title="The block, in four lines", body="""
<p>Modern (pre-norm) transformer block, exactly as implemented:</p>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-sm leading-7 text-ink-100">
x = x + Attention(Norm(x))<br>
x = x + FFN(Norm(x))
</p>
<p>Two sub-layers. Each one <strong>normalises a copy</strong> of the input, computes something, and <strong>adds the result back</strong> to the untouched original. Note what is <em>not</em> happening: nothing is ever overwritten. Each sub-layer contributes an increment.</p>
<p>The division of labour is clean:</p>
<ul>
  <li><strong>Attention moves information between positions.</strong> It is the only part of the model that looks sideways.</li>
  <li><strong>The FFN transforms each position independently.</strong> It never looks sideways at all.</li>
</ul>
<p>Interleaving them is what lets a stack of blocks build progressively richer, context-aware representations: gather, process, gather, process.</p>
""", figure=fig("viz-block", "Dataflow through a block",
                "Follow a vector through both sub-layers. Toggle the residual connections off to see what breaks.")),
        dict(title="Residual connections", body="""
<p>The <code>x +</code> is easy to overlook and is doing two crucial jobs.</p>
<p><strong>Gradient flow.</strong> In a plain deep stack, the gradient is multiplied by each layer's Jacobian on the way back; over 96 layers those factors compound and the signal explodes or vanishes. A residual connection gives the gradient an identity path — an additive route straight from the loss to the earliest layers. Without it, models this deep would not train at all.</p>
<p><strong>The residual stream as a channel.</strong> The more modern reading: the vector flowing through the model is a shared communication bus. Every sub-layer <em>reads</em> from it (through its projection matrices) and <em>writes</em> to it (by adding). An early layer can deposit a piece of information that a layer 40 blocks later retrieves, without any intervening layer needing to preserve it deliberately.</p>
<p>This picture also explains a practical fact: because everything is added into one stream, features occupy directions in that space, and different circuits communicate by writing to and reading from different directions.</p>
"""),
        dict(title="Normalisation, and where to put it", body="""
<p><strong>LayerNorm</strong> takes the vector at a position, subtracts its mean, divides by its standard deviation, then scales and shifts by learned parameters <code>γ</code> and <code>β</code>. It keeps activation magnitudes in a stable range so that training does not drift into overflow or collapse.</p>
<p><strong>RMSNorm</strong> drops the mean subtraction and the shift, dividing only by the root-mean-square. It is cheaper, empirically just as good, and is what Llama and most recent models use.</p>
<p>The placement question turned out to matter more than the choice of norm:</p>
<ul>
  <li><strong>Post-norm</strong> (original 2017): <code>x = Norm(x + Sublayer(x))</code>. The residual path itself gets normalised, which weakens the clean identity route. Deep post-norm models need careful learning-rate warmup and are prone to divergence.</li>
  <li><strong>Pre-norm</strong> (everything modern): <code>x = x + Sublayer(Norm(x))</code>. The residual path stays untouched all the way from input to output. Far more stable, trains at higher learning rates, scales to great depth.</li>
</ul>
<p>One consequence of pre-norm: the residual stream itself is never normalised on its way through, so its magnitude grows steadily with depth — visible in the figure below. Every pre-norm model therefore ends with a final norm after the last block, before the output projection. It is not an optional extra; without it the unbounded stream hits the output projection directly.</p>
""", figure=fig("viz-norm", "Pre-norm vs post-norm",
                "Simulated activation magnitude through a deep stack under both placements.")),
        dict(title="Counting the parameters", body="""
<p>For one block with <code>d = d_model</code> and a 4× FFN, ignoring biases and norm parameters:</p>
<div class="overflow-x-auto"><table>
<tr><th>Component</th><th>Shapes</th><th>Parameters</th></tr>
<tr><td>W_Q, W_K, W_V, W_O</td><td>four of [d, d]</td><td>4d²</td></tr>
<tr><td>FFN up and down</td><td>[4d, d] and [d, 4d]</td><td>8d²</td></tr>
<tr><td><strong>Total per block</strong></td><td></td><td><strong>12d²</strong></td></tr>
</table></div>
<p>So a 32-layer model with <code>d_model = 4096</code> holds roughly <code>32 × 12 × 4096²</code> ≈ 6.4 billion parameters in its blocks, plus the embedding table. The useful rule of thumb: <strong>parameters ≈ 12 × n_layers × d_model²</strong>, with about two thirds of it in the feed-forward networks.</p>
"""),
    ],
    exercises=[
        dict(type="order",
             prompt="<p>Put the operations of one modern pre-norm transformer block in order.</p>",
             items=["Normalise the input vector",
                    "Run multi-head attention on the normalised copy",
                    "Add the attention output back to the original vector",
                    "Normalise the updated vector",
                    "Run the feed-forward network on it",
                    "Add the FFN output back"],
             explain="Norm → attend → add → norm → FFN → add. The original vector is never replaced; each sub-layer adds a correction to the residual stream."),
        dict(type="mcq",
             prompt="<p>What is the primary reason residual connections make very deep transformers trainable?</p>",
             options=["They reduce the parameter count",
                      "They give gradients an additive identity path back to early layers, avoiding vanishing or exploding through 90+ multiplications",
                      "They normalise activations to unit variance",
                      "They let attention see future tokens"],
             answer="1",
             explain="Normalisation is what handles activation scale; residuals handle gradient flow and give layers a shared channel to communicate through."),
        dict(type="mcq",
             prompt="<p>Which sub-layer of a transformer block moves information <em>between</em> token positions?</p>",
             options=["The feed-forward network",
                      "The normalisation layer",
                      "Attention",
                      "Both attention and the feed-forward network"],
             answer="2",
             explain="Attention alone. The FFN is applied position-by-position and never looks sideways — which is exactly why it parallelises perfectly."),
        dict(type="numeric",
             prompt="<p>Using the rule <code>12 × n_layers × d_model²</code>, estimate the block parameters of a model with 40 layers and <code>d_model = 5120</code>. Give the answer in billions, to one decimal place.</p>",
             answer="12.6", tolerance=0.4,
             placeholder="billions",
             explain="12 × 40 × 5120² = 12 × 40 × 26,214,400 ≈ 1.26 × 10¹⁰, so about 12.6 billion parameters in the blocks, before the embedding table."),
        dict(type="mcq",
             prompt="<p>Why did the field move from post-norm to pre-norm placement?</p>",
             options=["Pre-norm is cheaper to compute",
                      "Post-norm normalises the residual path itself, degrading the clean gradient highway and making deep stacks unstable",
                      "Pre-norm removes the need for learned scale parameters",
                      "Post-norm is incompatible with RoPE"],
             answer="1",
             explain="Pre-norm keeps the residual path a pure sum from input to output. That stability is what allowed depth to scale past a couple of dozen layers without elaborate warmup schedules."),
    ],
))

# ------------------------------------------------------------------ 9
LESSONS.append(dict(
    part="Part II · The transformer",
    title="The full forward pass",
    blurb="Assemble everything: text in at the top, a probability distribution out at the bottom, with every shape accounted for.",
    viz=True,
    goals=[
        "Trace a tensor's shape through an entire model",
        "Explain the unembedding step and logits",
        "Describe what changes as depth increases",
        "Explain why only the last position matters at generation time",
    ],
    recap="Tokenize, embed to [T, d], pass through N blocks keeping [T, d] throughout, apply a final norm, project to [T, vocab] logits, and softmax the last row into next-token probabilities.",
    sections=[
        dict(title="End to end, with shapes", body="""
<p>Take a 7-token prompt through a model with <code>d_model = 4096</code>, 32 layers, vocabulary 128,000.</p>
<div class="overflow-x-auto"><table>
<tr><th>Step</th><th>Operation</th><th>Shape after</th></tr>
<tr><td>1</td><td>Tokenize the text</td><td>[7] integer ids</td></tr>
<tr><td>2</td><td>Embedding lookup</td><td>[7, 4096]</td></tr>
<tr><td>3</td><td>Block 1 … block 32 (RoPE applied inside each attention)</td><td>[7, 4096] throughout</td></tr>
<tr><td>4</td><td>Final normalisation</td><td>[7, 4096]</td></tr>
<tr><td>5</td><td>Unembedding projection [4096, 128000]</td><td>[7, 128000] logits</td></tr>
<tr><td>6</td><td>Take the last row, softmax it</td><td>[128000] probabilities</td></tr>
</table></div>
<p>The single most important thing on that table: <strong>the shape never changes through the entire stack</strong>. Every block maps <code>[T, d]</code> to <code>[T, d]</code>. The blocks are shape-compatible with each other, which is why you can stack 32 or 96 of them without altering anything else.</p>
""", figure=fig("viz-forward", "Watch a tensor flow",
                "Step through the pass and see the shape and a sample of values at each stage.")),
        dict(title="Logits and the unembedding", body="""
<p>The final projection produces one <strong>logit</strong> per vocabulary entry per position — an unnormalised score. Softmax converts a row of logits into probabilities:</p>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-sm text-ink-100">P(token i) = exp(logit_i) / Σⱼ exp(logit_j)</p>
<p>If the output matrix is tied to the input embedding table (common), each logit is literally the dot product of the final residual vector with a token's embedding. The prediction becomes: <em>which token's embedding has the largest dot product with my final vector?</em> Lesson 3's geometry, closing the loop — and note it is the dot product, not the cosine, so a token whose embedding is long is easier to predict than a short one pointing the same way.</p>
<p>Note that logits themselves are what get manipulated at generation time — temperature, top-k, penalties all operate on logits before the softmax. That is Lesson 10.</p>
"""),
        dict(title="What the layers do, roughly", body="""
<p>Probing studies across many models find a consistent rough progression. Treat it as a tendency, not a law — the boundaries are soft and features are distributed.</p>
<ul>
  <li><strong>Early layers</strong> resolve surface form: detokenization (stitching word-pieces back into a concept), part of speech, immediate local context.</li>
  <li><strong>Middle layers</strong> carry the heaviest lifting: syntax, entity tracking, factual recall, coreference. Interpretability work locates much factual knowledge in mid-layer feed-forward networks.</li>
  <li><strong>Late layers</strong> move from "what is being said" to "what token comes next", sharpening toward the vocabulary — increasingly task- and output-specific.</li>
</ul>
<p>This progression is why techniques like early-exit and layer-skipping work at all for easy tokens, and why probing a middle layer is often the best place to read off a model's belief about a fact.</p>
""", figure=fig("viz-layers", "Prediction sharpening with depth",
                "A simulated view of how the top-token distribution concentrates as you read out from deeper layers.")),
        dict(title="Only the last row matters (when generating)", body="""
<p>The model computes logits at every position, but when generating the next token you only need the last row. Why compute the rest?</p>
<p><strong>During training</strong>, you need all of them. One pass over a 4096-token document yields 4096 separate predictions and 4096 loss terms — every position predicts its own successor. That parallelism over positions is precisely why transformers train efficiently and why the causal mask is essential.</p>
<p><strong>During generation</strong>, all earlier positions produce logits you discard. Worse, without caching you would recompute the entire prefix for every single new token. The fix is the KV cache, which is Lesson 11 — and it splits inference into two phases with completely different performance characteristics.</p>
"""),
    ],
    exercises=[
        dict(type="mcq",
             prompt="<p>A 12-token prompt enters a model with <code>d_model = 768</code>. What is the shape of the activations between block 5 and block 6?</p>",
             options=["[12, 768]", "[768, 12]", "[12, 50257]", "[1, 768]"],
             answer="0",
             explain="Every block preserves [T, d]. It is [12, 768] between every pair of blocks — that invariance is what makes the stack composable."),
        dict(type="fill",
             prompt="<p>What is the name for the raw, unnormalised scores the model produces for each vocabulary entry before softmax is applied?</p>",
             answer=["logits", "logit"],
             placeholder="one word",
             explain="Logits. Sampling controls like temperature and top-k operate on logits, before the softmax converts them to probabilities."),
        dict(type="numeric",
             prompt="<p>With <code>d_model = 4096</code> and a vocabulary of 128,000, how many parameters are in the unembedding projection, in millions? (Ignore bias.)</p>",
             answer="524", tolerance=5,
             placeholder="millions",
             explain="4096 × 128,000 = 524,288,000, about 524 million. Half a billion parameters in the output layer alone, which is exactly why many models tie it to the input embedding table."),
        dict(type="mcq",
             prompt="<p>During <em>training</em>, why does the model compute logits at every position rather than only the last one?</p>",
             options=["To make the softmax numerically stable",
                      "Because each position predicts its own next token, giving T training signals from one forward pass",
                      "Because the causal mask requires it",
                      "To fill the KV cache"],
             answer="1",
             explain="A 4096-token document produces 4096 prediction tasks in a single pass. This dense supervision is a large part of why pretraining is data-efficient per forward pass."),
        dict(type="order",
             prompt="<p>Order the stages of a full forward pass.</p>",
             items=["Map tokens to ids and look up embeddings",
                    "Run the stack of transformer blocks",
                    "Apply the final normalisation",
                    "Project to vocabulary size to get logits",
                    "Softmax the final position into a probability distribution"],
             explain="Embed → blocks → final norm → unembed → softmax. The shape is [T, d] from the embedding all the way to the final norm."),
    ],
))

# ------------------------------------------------------------------ 10
LESSONS.append(dict(
    part="Part III · Generation",
    title="Sampling: turning probabilities into text",
    blurb="The model gives you a distribution. Choosing a token from it is a separate, tunable decision — and it changes output quality more than most people expect.",
    viz=True,
    goals=[
        "Explain greedy, temperature, top-k and top-p sampling precisely",
        "Predict how a distribution reshapes as temperature changes",
        "Choose sensible settings for factual versus creative tasks",
        "Explain repetition penalties, beam search and their failure modes",
    ],
    recap="Temperature divides logits before the softmax: below 1 sharpens, above 1 flattens. Top-k keeps the k best tokens, top-p keeps the smallest set whose probability sums to p. Truncation removes the long tail of bad tokens; temperature controls the shape of what remains.",
    sections=[
        dict(title="Greedy is not obviously right", body="""
<p>The simplest rule is to always take the highest-probability token. It is deterministic and reproducible. It is also, for open-ended text, noticeably bad: greedy output falls into loops and repetitive, flat phrasing.</p>
<p>The reason is worth understanding. Human text is not the most probable text. At every position, natural writing takes a moderately likely option rather than the single most likely one; always choosing the mode produces something statistically unlike real language. Greedy decoding also has no way out of a repetition loop — if "the same the same" becomes locally most likely, it stays there forever.</p>
<p>For short factual answers or code, greedy (or temperature 0) is often exactly right. For anything longer or open-ended, you want randomness.</p>
"""),
        dict(title="Temperature", body="""
<p>Temperature divides the logits before the softmax:</p>
<p class="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 font-mono text-sm text-ink-100">P(i) = softmax(logit_i / T)</p>
<ul>
  <li><strong>T &lt; 1</strong> — logits spread apart, gaps amplify, the distribution sharpens toward the top token. More focused, more repetitive.</li>
  <li><strong>T = 1</strong> — the model's own distribution, untouched.</li>
  <li><strong>T &gt; 1</strong> — logits compress toward each other, the distribution flattens. More varied, and past roughly 1.3 usually incoherent.</li>
  <li><strong>T → 0</strong> — becomes greedy decoding. Implementations special-case it rather than dividing by zero.</li>
</ul>
<p>The important intuition: temperature does <strong>not</strong> add new information or make the model smarter or dumber. It reweights the same ranking. A token the model considers hopeless is still nearly hopeless at T = 1.5 — just slightly less so, which is exactly where incoherence comes from.</p>
""", figure=fig("viz-temperature", "Temperature, live",
                "Drag temperature and watch the same logits become a different distribution. Try 0.2 and 1.8.")),
        dict(title="Truncation: top-k and top-p", body="""
<p>Even at moderate temperature, the tail of the distribution contains thousands of tokens that are individually near-zero but collectively hold real probability mass. Sample long enough and you will eventually draw one, derailing the text. Truncation removes the tail before sampling.</p>
<p><strong>Top-k</strong> — keep the k highest-probability tokens, renormalise, sample. Simple, but k is fixed regardless of context: when the model is confident, k = 50 admits 49 bad options; when it is genuinely uncertain across 200 reasonable tokens, k = 50 cuts off good ones.</p>
<p><strong>Top-p (nucleus)</strong> — sort by probability and keep the smallest set whose cumulative probability reaches p (typically 0.9–0.95). The set size adapts automatically: a couple of tokens when the model is sure, hundreds when it is not. This is the modern default.</p>
<p><strong>Min-p</strong> — a newer variant: keep tokens whose probability is at least <code>p × (probability of the top token)</code>. Robust at high temperatures, and increasingly available.</p>
<p>The usual ordering in an implementation is: apply penalties to logits → divide by temperature → truncate (top-k, then top-p) → renormalise → sample.</p>
""", figure=fig("viz-truncation", "Top-k and top-p side by side",
                "Set k and p and see which tokens survive under each rule. Move the temperature slider to change how confident the model is, and watch only the top-p set resize.")),
        dict(title="Penalties, beam search, and choosing settings", body="""
<p><strong>Repetition and frequency penalties</strong> subtract from the logits of tokens that already appeared. They reduce loops, but they are blunt instruments — they also penalise words that legitimately recur, such as a variable name in code or a subject's name in an essay. Keep them low or off for code.</p>
<p><strong>Beam search</strong> keeps several candidate continuations alive and expands the best-scoring ones, aiming for a high-probability whole sequence rather than a high-probability next token. It is standard in translation, where there is one right answer, and poor for open-ended text, where it produces bland, generic output — again because likely text is not human text.</p>
<p>Sensible starting points:</p>
<div class="overflow-x-auto"><table>
<tr><th>Task</th><th>Temperature</th><th>Notes</th></tr>
<tr><td>Factual Q&amp;A, extraction, classification</td><td>0</td><td>Deterministic and reproducible</td></tr>
<tr><td>Code generation</td><td>0 – 0.3</td><td>No repetition penalty</td></tr>
<tr><td>General assistant prose</td><td>0.7</td><td>top-p 0.9–0.95</td></tr>
<tr><td>Brainstorming, fiction</td><td>0.9 – 1.1</td><td>top-p 0.95, expect to discard some outputs</td></tr>
</table></div>
<div class="note note-warn"><p class="text-sm"><strong>Temperature 0 is not fully deterministic in practice.</strong> Floating-point non-associativity, batching and GPU kernel scheduling can change results run to run on a real serving stack. Do not build a system that depends on bit-identical outputs.</p></div>
"""),
    ],
    exercises=[
        dict(type="mcq",
             prompt="<p>What does raising the temperature from 0.7 to 1.4 do to the distribution?</p>",
             options=["Adds new candidate tokens the model had not considered",
                      "Flattens it, so lower-ranked tokens get relatively more probability",
                      "Sharpens it toward the top token",
                      "Truncates the tail below a threshold"],
             answer="1",
             explain="Dividing logits by a larger number compresses the gaps between them, flattening the softmax. The ranking is unchanged; only the shape moves. Truncation is a separate mechanism."),
        dict(type="mcq",
             prompt="<p>The model gives probabilities <code>[0.6, 0.25, 0.1, 0.03, 0.02]</code>. Under top-p with p = 0.9, how many tokens remain in the candidate set?</p>",
             options=["1", "2", "3", "5"],
             answer="2",
             explain="Cumulative: 0.6, then 0.85, then 0.95. Two tokens are not enough to reach 0.9, so the third is included and the set is 3 tokens. The last two are discarded."),
        dict(type="multi",
             prompt="<p>Which are genuine drawbacks of pure greedy decoding? Select all.</p>",
             options=["It can get stuck in repetition loops with no escape",
                      "It produces text that is statistically unlike human writing for long outputs",
                      "It makes the model's factual knowledge worse",
                      "It gives no diversity across runs of the same prompt"],
             answer=[0, 1, 3],
             explain="Greedy does not change what the model knows — the same distribution is being computed either way. It only changes which token is picked from it."),
        dict(type="mcq",
             prompt="<p>Why is top-p usually preferred over top-k?</p>",
             options=["It is faster to compute",
                      "The size of the candidate set adapts to how confident the model is at that step",
                      "It guarantees deterministic output",
                      "It works better with repetition penalties"],
             answer="1",
             explain="A fixed k is wrong in both directions depending on context. Nucleus sampling keeps a small set when the model is confident and a large one when it genuinely is not."),
        dict(type="numeric",
             prompt="<p>Two tokens have logits 2.0 and 1.0. At temperature 0.5, what is the probability of the higher one? Give two decimal places.</p>",
             answer="0.88", tolerance=0.02,
             placeholder="between 0 and 1",
             explain="Divide by T: logits become 4.0 and 2.0. exp(4)=54.6, exp(2)=7.39, so P = 54.6/62.0 ≈ 0.88. At T=1 the same pair gives 0.73 — halving the temperature widened the gap considerably."),
        dict(type="order",
             prompt="<p>Order the operations a typical sampling implementation applies to raw logits.</p>",
             items=["Apply repetition and frequency penalties to the logits",
                    "Divide the logits by the temperature",
                    "Truncate with top-k and top-p",
                    "Renormalise the surviving probabilities and draw a token"],
             explain="Penalties and temperature act on logits; truncation acts on the resulting ranking; then you renormalise and sample. Applying temperature after truncation would give quite different results."),
    ],
))
