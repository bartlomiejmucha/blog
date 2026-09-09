window.COURSE = {
  "lessons": [
    {
      "id": "l01",
      "num": 1,
      "title": "What a language model actually does",
      "file": "01-what-a-language-model-actually-does.html",
      "part": "Part I \u00b7 Foundations",
      "blurb": "Strip away the chat interface and an LLM is one function called over and over: given some text, guess what comes next.",
      "exercises": 6
    },
    {
      "id": "l02",
      "num": 2,
      "title": "Tokens: how text becomes numbers",
      "file": "02-tokens-how-text-becomes-numbers.html",
      "part": "Part I \u00b7 Foundations",
      "blurb": "The model never sees letters or words. Before any thinking happens, prompt is chopped into pieces and each piece is replaced by an integer ids from a fixed vocabulary built by a compression algorithm \u2014 and that detail explains a surprising number of LLM quirks.",
      "exercises": 5
    },
    {
      "id": "l03",
      "num": 3,
      "title": "Embeddings: meaning as direction",
      "file": "03-embeddings-meaning-as-direction.html",
      "part": "Part I \u00b7 Foundations",
      "blurb": "Each token id becomes a long list of numbers. Those numbers place the token in a space where geometric closeness means something like similarity of meaning.",
      "exercises": 5
    },
    {
      "id": "l04",
      "num": 4,
      "title": "Neurons, matrices and nonlinearity",
      "file": "04-neurons-matrices-and-nonlinearity.html",
      "part": "Part I \u00b7 Foundations",
      "blurb": "The last two lessons turned text into numbers and showed how numbers compare. But nothing in them yet <em>changes</em> a number \u2014 and the model is nothing but chained changes. This lesson builds the smallest possible change-maker, a single neuron, from scratch, then stacks it into the layers that fill a transformer block.",
      "exercises": 5
    },
    {
      "id": "l05",
      "num": 5,
      "title": "Attention: queries, keys and values",
      "file": "05-attention-queries-keys-and-values.html",
      "part": "Part II \u00b7 The transformer",
      "blurb": "The mechanism that made LLMs possible. Each position asks a question, every other position advertises what it has, and information flows where the match is strongest.",
      "exercises": 6
    },
    {
      "id": "l06",
      "num": 6,
      "title": "Multi-head attention",
      "file": "06-multi-head-attention.html",
      "part": "Part II \u00b7 The transformer",
      "blurb": "One attention head can only average one way. Running many in parallel, each in its own small subspace, lets a layer track several relationships at once.",
      "exercises": 5
    },
    {
      "id": "l07",
      "num": 7,
      "title": "Position: how the model knows word order",
      "file": "07-position-how-the-model-knows-word-order.html",
      "part": "Part II \u00b7 The transformer",
      "blurb": "Attention is order-blind by construction. Something has to tell the model that 'dog bites man' differs from 'man bites dog'.",
      "exercises": 5
    },
    {
      "id": "l08",
      "num": 8,
      "title": "The transformer block",
      "file": "08-the-transformer-block.html",
      "part": "Part II \u00b7 The transformer",
      "blurb": "Attention plus a feed-forward network, wrapped in residual connections and normalisation. This unit, repeated dozens of times, is the entire model.",
      "exercises": 5
    },
    {
      "id": "l09",
      "num": 9,
      "title": "The full forward pass",
      "file": "09-the-full-forward-pass.html",
      "part": "Part II \u00b7 The transformer",
      "blurb": "Assemble everything: text in at the top, a probability distribution out at the bottom, with every shape accounted for.",
      "exercises": 5
    },
    {
      "id": "l10",
      "num": 10,
      "title": "Sampling: turning probabilities into text",
      "file": "10-sampling-turning-probabilities-into-text.html",
      "part": "Part III \u00b7 Generation",
      "blurb": "The model gives you a distribution. Choosing a token from it is a separate, tunable decision \u2014 and it changes output quality more than most people expect.",
      "exercises": 6
    },
    {
      "id": "l11",
      "num": 11,
      "title": "Context windows and the KV cache",
      "file": "11-context-windows-and-the-kv-cache.html",
      "part": "Part III \u00b7 Generation",
      "blurb": "Why the first token of a response is slow and the rest are fast, why long prompts cost memory rather than just time, and what actually fills up when you 'run out of context'.",
      "exercises": 5
    },
    {
      "id": "l12",
      "num": 12,
      "title": "Pretraining: how the weights get their values",
      "file": "12-pretraining-how-the-weights-get-their-values.html",
      "part": "Part IV \u00b7 Training",
      "blurb": "Billions of parameters start as random noise. Gradient descent on next-token prediction, repeated trillions of times, turns them into a language model.",
      "exercises": 6
    },
    {
      "id": "l13",
      "num": 13,
      "title": "Scaling laws: why bigger worked",
      "file": "13-scaling-laws-why-bigger-worked.html",
      "part": "Part IV \u00b7 Training",
      "blurb": "Loss falls as a predictable power law in parameters, data and compute. That predictability is what justified spending hundreds of millions of dollars on a single training run.",
      "exercises": 5
    },
    {
      "id": "l14",
      "num": 14,
      "title": "Post-training: SFT, RLHF and DPO",
      "file": "14-post-training-sft-rlhf-and-dpo.html",
      "part": "Part IV \u00b7 Training",
      "blurb": "A pretrained model completes text; it does not answer questions. Turning a document-completer into an assistant is a separate stage, and it is where most of the behaviour you interact with comes from.",
      "exercises": 6
    },
    {
      "id": "l15",
      "num": 15,
      "title": "Prompting, in-context learning and chain of thought",
      "file": "15-prompting-in-context-learning-and-chain-of-thought.html",
      "part": "Part V \u00b7 Using and extending models",
      "blurb": "Why examples in the prompt work without changing a single weight, and why asking a model to think out loud measurably improves its answers.",
      "exercises": 5
    },
    {
      "id": "l16",
      "num": 16,
      "title": "RAG, tools and agents",
      "file": "16-rag-tools-and-agents.html",
      "part": "Part V \u00b7 Using and extending models",
      "blurb": "Weights are frozen, knowledge goes stale and models cannot check anything. Retrieval and tool use fix that by putting the right text in the context and letting the model call out to real systems.",
      "exercises": 5
    },
    {
      "id": "l17",
      "num": 17,
      "title": "Making models cheap: quantization, LoRA, MoE, speculative decoding",
      "file": "17-making-models-cheap-quantization-lora-moe-speculative-decoding.html",
      "part": "Part V \u00b7 Using and extending models",
      "blurb": "The techniques that determine whether a model costs $10 or $10,000 per million tokens to serve \u2014 and how a 7B model ends up running on a laptop.",
      "exercises": 6
    },
    {
      "id": "l18",
      "num": 18,
      "title": "Evaluation, hallucination and what is still unsolved",
      "file": "18-evaluation-hallucination-and-what-is-still-unsolved.html",
      "part": "Part V \u00b7 Using and extending models",
      "blurb": "How to tell whether a model is actually good, why it makes things up, and an honest account of the open problems.",
      "exercises": 6
    }
  ]
};
