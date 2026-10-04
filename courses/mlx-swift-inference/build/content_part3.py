# -*- coding: utf-8 -*-
"""Part III — The server. Lessons 11-15."""
from codeblocks import block, source

def fig(fid, title, sub, body=""):
    return ('<div class="figure" id="%s">'
            '<p class="figure-title">%s</p>'
            '<p class="figure-sub">%s</p>%s</div>') % (fid, title, sub, body)

MAIN = "Sources/serve/main.swift"
API = "Sources/serve/OpenAI.swift"
ENGINE = "Sources/Inference/Engine.swift"

LESSONS = []

# ------------------------------------------------------------------ 11
LESSONS.append(dict(
    part="Part III · The server",
    title="An OpenAI-compatible API with Hummingbird",
    blurb="Put an HTTP front on the engine that speaks the Chat Completions wire format, so every existing OpenAI client and SDK can use your server unchanged.",
    viz=False,
    goals=[
        "Set up a Hummingbird router with health, models and chat completion routes",
        "Decode the Chat Completions request, including fields clients send in several shapes",
        "Encode responses in the exact JSON shape clients expect",
        "Return useful errors instead of crashing on bad input",
    ],
    recap="Hummingbird maps routes to async closures. The chat route decodes the request, renders the prompt, submits a GenerationRequest to the engine, and either streams or collects the resulting events. Snake-case JSON strategies keep the Swift types idiomatic while matching OpenAI's field names exactly.",
    sections=[
        dict(title="Why the OpenAI format", body="""
<p>You could invent your own API. Don't. The Chat Completions format has become the common language of LLM servers: the official OpenAI SDKs, LangChain, editor plugins and countless scripts all speak it, and they only need a different base URL to talk to yours. Matching it costs a few Codable structs.</p>
<p>The server needs four routes:</p>
<table>
<tr><th>Route</th><th>Purpose</th></tr>
<tr><td><code>GET /health</code></td><td>liveness check for scripts and load balancers</td></tr>
<tr><td><code>GET /v1/models</code></td><td>lists the model id; many clients call it on startup</td></tr>
<tr><td><code>POST /v1/chat/completions</code></td><td>the real work, streaming or not</td></tr>
<tr><td><code>GET /metrics</code></td><td>Prometheus counters (Lesson 21)</td></tr>
</table>
"""),
        dict(title="Startup", body="""
""" + source(MAIN, "// Usage: serve", 'print("loaded') + """
<p>Startup loads the model once, picks an engine (the serial engine with MTP by default, or the batching engine of Lesson 15), and creates the shared objects the routes use. Everything here is created before the server accepts its first connection, so no request ever waits for a model to load.</p>
""" + source(MAIN, "let router = Router()", 'router.post("v1/chat/completions")', include_end=False) + """
<p>A Hummingbird route is an async closure that receives the request and a context and returns anything that can become a response: a <code>String</code>, or a <code>Response</code> you build yourself. The application at the bottom of the file binds to localhost:</p>
""" + source(MAIN, "let app = Application(", "try await app.runService()") + """
<p>Binding to <code>127.0.0.1</code> keeps the server off the network. It has no authentication, so exposing it is a deliberate decision, not a default (Lesson 21).</p>
"""),
        dict(title="Decoding the request", body="""
""" + source(API, "struct ChatRequest: Decodable") + """
<p>Two details worth copying:</p>
<ul>
<li><strong>Snake case without coding keys.</strong> The shared decoder uses <code>convertFromSnakeCase</code>, so <code>max_completion_tokens</code> lands in <code>maxCompletionTokens</code>. The encoder does the reverse for responses.</li>
<li><strong>Fields with several shapes.</strong> OpenAI accepts <code>stop</code> as a string or a list. A small enum with a custom <code>init(from:)</code> accepts both. Clients rely on such details, and a strict decoder that rejects a valid request is a compatibility bug.</li>
</ul>
<p><code>messages</code> and <code>tools</code> are not in this struct. Their contents go straight into the Jinja chat template, which wants untyped dictionaries, and modelling every possible message shape (text, tool calls, tool results, image parts) in Swift types would only be converted back again. The route reads them separately with <code>JSONSerialization</code>:</p>
""" + source(MAIN, 'router.post("v1/chat/completions")', "        stop: chat.stop?.list ?? [])") + """
<p>The body size is capped at 4 MB before anything is parsed, malformed JSON or an empty message list returns HTTP 400 with an OpenAI-style error body, and missing sampling fields get defaults. The result is a <code>GenerationRequest</code>: token ids, sampling parameters, a token limit and stop strings. That is everything the engine needs, and nothing about HTTP.</p>
"""),
        dict(title="Submitting and answering", body="""
""" + source(MAIN, "    let submitted:", "    let events = instrument(submitted)") + """
<p><code>engine.submit</code> returns immediately with an <code>AsyncThrowingStream</code> of events: text pieces, then one <code>.finished</code> with the reason and token counts. If the engine's queue is full it throws, and the client gets HTTP 429 at once. <code>instrument</code> wraps the stream to record metrics (Lesson 21).</p>
<p>A non-streaming request simply collects the stream:</p>
""" + source(MAIN, '    var text = ""', "        usage: usageBody(usage)))") + """
<p>and encodes it in the response shape clients expect:</p>
""" + source(API, "struct ChatCompletion: Encodable") + source(MAIN, "func json(") + """
<p>The <code>finish_reason</code> values matter to clients: <code>stop</code> means the model ended its turn or hit a stop string, <code>length</code> means the token limit cut it off, and <code>tool_calls</code> means the model wants a function called. <code>usage.prompt_tokens_details.cached_tokens</code> reports how much of the prompt the cache covered (Lesson 14).</p>
"""),
        dict(title="Try it with an SDK", body="""
""" + block('''from openai import OpenAI
client = OpenAI(base_url="http://localhost:8080/v1", api_key="unused")
reply = client.chat.completions.create(
    model="qwen3.5-0.8b",
    messages=[{"role": "user", "content": "One sentence on unified memory."}],
    temperature=0,
)
print(reply.choices[0].message.content)''', "text") + """
<p>The SDK requires an API key and a model name; the server ignores both. Everything else, including streaming in the next lesson, works without changes.</p>
"""),
    ],
    exercises=[
        dict(type="mcq", prompt="<p>A client sends <code>\"stop\": \"###\"</code> and your decoder only accepts arrays. What happens?</p>",
             options=["The stop string is ignored",
                      "The request fails to decode and the client gets HTTP 400, though it was valid by OpenAI's rules",
                      "The server crashes",
                      "Nothing; JSON decoders convert automatically"], answer=1,
             explain="<p>Codable is strict about types. Accepting every shape the official API accepts is part of being compatible.</p>"),
        dict(type="mcq", prompt="<p>Why does the route read <code>messages</code> with JSONSerialization instead of a Codable struct?</p>",
             options=["Codable cannot decode arrays",
                      "The messages go directly into the Jinja template, which wants untyped dictionaries; typed structs would be converted straight back",
                      "JSONSerialization is faster",
                      "To support XML"], answer=1,
             explain="<p>Messages can contain text, tool calls, tool results and more. Passing them through untouched supports all of them with no extra code.</p>"),
        dict(type="fill", prompt="<p>Which <code>finish_reason</code> tells a client that generation was cut off by the token limit?</p>",
             answer=["length"], placeholder="value",
             explain="<p><code>length</code>. Clients often show a \"continue\" option when they see it.</p>"),
        dict(type="mcq", prompt="<p>Why does the server bind to 127.0.0.1 by default?</p>",
             options=["It is faster",
                      "The server has no authentication, so it should not be reachable from the network unless you choose that",
                      "Hummingbird cannot bind elsewhere",
                      "IPv6 is not supported"], answer=1,
             explain="<p>Anyone who can reach an unauthenticated inference server can use your GPU. Listening on localhost only is the safe default.</p>"),
    ],
))

# ------------------------------------------------------------------ 12
LESSONS.append(dict(
    part="Part III · The server",
    title="Streaming and cancellation",
    blurb="Send each piece of text the moment it exists with server-sent events, and stop generating the instant a client goes away so the GPU is never wasted on nobody.",
    viz=False,
    goals=[
        "Write a server-sent event stream in the Chat Completions chunk format",
        "Connect the engine's AsyncThrowingStream to the HTTP response body",
        "Propagate a client disconnect back to the worker as cancellation",
        "Explain why cancellation is a throughput feature, not a nicety",
    ],
    recap="A streamed response is a sequence of 'data: {json}' lines separated by blank lines, ending with 'data: [DONE]'. Hummingbird's ResponseBody gives the route a writer; the route loops over the engine's event stream and writes one chunk per text piece. When the client disconnects, the write throws, the loop ends, the stream terminates, and its onTermination handler flips the job's cancelled flag, which the worker checks after every token.",
    sections=[
        dict(title="Server-sent events", body="""
<p>Streaming in the OpenAI API uses <strong>server-sent events</strong> (SSE), the simplest streaming format on the web: a long-lived HTTP response with content type <code>text/event-stream</code>, made of lines starting with <code>data: </code>, each event followed by a blank line.</p>
""" + block('''data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant"}}]}

data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Here"}}]}

data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":" is"}}]}

data: {"id":"chatcmpl-1","object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{...}}

data: [DONE]''', "text") + """
<p>The first chunk carries the role, each following chunk a <code>delta</code> with new content, the last one the finish reason (and, in this server, the token usage), and <code>[DONE]</code> closes the stream. Clients concatenate the deltas.</p>
""" + source(API, "struct ChatChunk: Encodable") + """
"""),
        dict(title="Writing the stream", body="""
""" + source(MAIN, "    if chat.stream == true {", "            })") + """
<p><code>ResponseBody { writer in ... }</code> hands the route a writer for the response body. Hummingbird sends the headers right away and keeps the connection open while the closure runs. Inside, the route iterates the engine's event stream with <code>for try await</code> and writes one SSE chunk per event. Each <code>write</code> goes out to the socket as soon as it is called, so the client sees each token within milliseconds of the worker producing it.</p>
<p>The <code>buffered</code> logic in the middle holds text back once it might be the start of a tool call, so tool calls go out as one structured chunk. Lesson 21 explains it; without tools, every text event goes straight through.</p>
"""),
        dict(title="The bridge: AsyncThrowingStream", body="""
<p>The worker is an ordinary thread producing tokens in a loop. The HTTP route is async Swift code. <code>AsyncThrowingStream</code> connects them:</p>
""" + source(ENGINE, "    public func submit(_ request: GenerationRequest) throws") + "\n" + """
<p><code>makeStream</code> returns the stream, which the route consumes, and its continuation, which the worker keeps. The worker calls <code>continuation.yield(.text(...))</code> for each piece and <code>finish()</code> at the end; these calls are thread-safe, so the worker thread never has to touch Swift concurrency. Events are buffered until the consumer reads them, so a slow client does not slow the worker.</p>
"""),
        dict(title="Cancellation", body="""
<p>The most important line in <code>submit</code> is this one:</p>
""" + block('''continuation.onTermination = { _ in job.cancel() }''', "swift") + """
<p>Follow what happens when a user closes the browser tab halfway through a long answer:</p>
<ol>
<li>The next <code>writer.write</code> in the route throws, because the socket is gone.</li>
<li>The error ends the <code>for try await</code> loop, and the stream's consumer goes away.</li>
<li>The stream terminates and calls <code>onTermination</code>, which sets the job's cancelled flag.</li>
<li>The worker checks the flag after every token and stops:</li>
</ol>
""" + source(ENGINE, "final class Job: Sendable") + """
<p>The flag is behind an <code>OSAllocatedUnfairLock</code>, so setting it from an HTTP thread and reading it from the worker is safe. Checking once per token costs nothing measurable.</p>
<p>Why this matters: without it, an abandoned 2,000-token request keeps the GPU busy for half a minute, and every queued request waits behind it. In the finished server, a request sent one second after a client disconnected mid-stream from such a request was answered in 0.2 seconds. Cancellation is a throughput feature.</p>
"""),
    ],
    exercises=[
        dict(type="mcq", prompt="<p>How does an SSE client know where one event ends?</p>",
             options=["Each event has a length header", "A blank line follows each event",
                      "Events are fixed-size", "The connection closes after each event"], answer=1,
             explain="<p>SSE is line-based: one or more <code>data:</code> lines, then an empty line.</p>"),
        dict(type="order", prompt="<p>A client disconnects mid-stream. Order what happens next.</p>",
             items=["The route's next write throws", "The for-await loop over events ends",
                    "The stream terminates and calls onTermination", "The job's cancelled flag is set",
                    "The worker sees the flag after the current token and stops"],
             explain="<p>The disconnect is noticed on the next write; termination of the stream is the hand-off point between HTTP and the engine.</p>"),
        dict(type="mcq", prompt="<p>Why can the worker thread call <code>continuation.yield</code> without being part of Swift concurrency?</p>",
             options=["It cannot; it must be an actor",
                      "The continuation is thread-safe and buffers events until the async consumer reads them",
                      "yield blocks until the client reads",
                      "Hummingbird runs on the worker thread"], answer=1,
             explain="<p>AsyncStream continuations are designed to be fed from any thread, which makes them the standard bridge from callback or thread-based code to async code.</p>"),
        dict(type="mcq", prompt="<p>Without cancellation, what is the main cost of a client that disconnects early?</p>",
             options=["A memory leak in Hummingbird",
                      "The worker keeps generating for nobody, and every queued request waits behind it",
                      "The model's weights get corrupted",
                      "The client is charged twice"], answer=1,
             explain="<p>The single GPU worker is the scarcest resource. Wasting it delays everyone else.</p>"),
    ],
))

# ------------------------------------------------------------------ 13
LESSONS.append(dict(
    part="Part III · The server",
    title="One GPU, many clients",
    blurb="Many HTTP requests arrive at once, but the model must run on one thread at a time. Build the serial engine: a dedicated worker thread, a locked inbox, backpressure, and a clear rule for which objects each thread may touch.",
    viz=False,
    goals=[
        "Explain why model work belongs on one dedicated thread",
        "Hand work between threads with a locked queue and a semaphore",
        "Reject excess load early with a bounded queue",
        "Reason about Sendable in a server that wraps non-thread-safe libraries",
    ],
    recap="All MLX work happens on one dedicated worker thread, because the GPU serializes the work anyway and the model objects are not thread-safe. Requests cross from HTTP threads to the worker through an inbox protected by a lock, with a semaphore to wake the worker. The inbox is bounded, so overload becomes a fast 429 instead of an ever-growing wait. Objects only the worker touches are marked @unchecked Sendable with that rule written next to them.",
    sections=[
        dict(title="Why one thread", body="""
<p>Hummingbird serves each connection on Swift's cooperative thread pool, so dozens of requests can be in flight at once. It is tempting to run the model right there in the route. Three reasons not to:</p>
<ul>
<li><strong>The GPU does one thing at a time anyway.</strong> Two forward passes submitted together do not finish faster than one after the other; they just compete. Concurrency at the model level only helps when it is designed in, which is what batching (Lesson 15) does.</li>
<li><strong>The model is not thread-safe.</strong> Caches are mutated in place, MLX modules are classes, and nothing guards them. Two threads in one forward pass corrupt state silently.</li>
<li><strong>The cooperative pool must not block.</strong> It has about one thread per CPU core. A route that spends ten seconds generating holds one of them hostage, and a few long requests can stall every other async task in the process, including the HTTP server itself.</li>
</ul>
<p>So model work goes to one thread the engine owns, created for that purpose and nothing else.</p>
"""),
        dict(title="The serial engine", body="""
""" + source(ENGINE, "public final class SerialEngine", "    public var queueDepth", include_end=False) + """
<p>The worker is a plain <code>Thread</code> with a 16 MB stack. Deep model graphs build deep call stacks, and the default secondary-thread stack of 512 KB is not enough. It runs <code>run()</code> forever:</p>
""" + source(ENGINE, "    private func run()") + """
<p>The hand-off uses two primitives:</p>
<ul>
<li><strong>The inbox</strong> is an array behind an <code>OSAllocatedUnfairLock</code>. <code>submit</code>, running on an HTTP thread, appends under the lock; the worker removes the first job under the lock. The lock is held for microseconds, never across model work.</li>
<li><strong>The semaphore</strong> lets the worker sleep without spinning. Each submit signals it once; each loop iteration waits once. If ten jobs arrive while the worker is busy, the count reaches ten, and the worker runs ten iterations without sleeping.</li>
</ul>
<p>A job cancelled while it was still waiting is finished immediately without touching the model.</p>
"""),
        dict(title="Backpressure", body="""
<p>Without a limit, an overloaded server accepts every request and makes each one wait longer. Clients time out, retry, and make it worse. The inbox therefore has a maximum length (16 by default), and <code>submit</code> throws <code>queueFull</code> beyond it. The route turns that into HTTP 429 "server busy, retry later" at once.</p>
<p>A fast, honest no is better than a slow failure. Clients and load balancers know what to do with 429: back off, or try another server. The <code>queueDepth</code> property and the <code>qwenserve_rejected_total</code> metric let you see when it happens and size the limit.</p>
"""),
        dict(title="Sendable, honestly", body="""
<p>Swift 6 checks at compile time that values shared between threads are safe to share (<code>Sendable</code>). MLX arrays and modules are not, and the engine holds them, so the compiler cannot prove the engine safe. The options:</p>
<ol>
<li>Make the engine an actor. Actor methods run on the cooperative pool, which brings back the blocking problem above, unless you give the actor a custom executor.</li>
<li>Mark the engine <code>@unchecked Sendable</code> and enforce a rule by design.</li>
</ol>
<p>The engine takes option 2, and the rule is written in the code: the model, the prompt cache and the generators are touched only by the worker thread; everything shared (the inbox, the semaphore, each job's cancelled flag) is protected by a lock or is itself thread-safe. <code>@unchecked</code> is not a way to silence the compiler; it moves the proof from the compiler to you, so the proof has to be short enough to check by reading.</p>
<p>The same reasoning gives <code>PromptFormatter</code>, which renders chat templates on HTTP threads. The tokenizer is not documented as thread-safe, so every call goes through a lock:</p>
""" + source("Sources/Inference/LoadedModel.swift", "public final class PromptFormatter") + """
<p>Rendering takes well under a millisecond, so the lock never becomes a bottleneck, and the worker never renders templates, so it never waits on HTTP threads.</p>
"""),
        dict(title="One request at a time", body="""
<p>This engine serves requests strictly one after another. While one request decodes, the others wait in the inbox. For a personal server that is often exactly right: each request gets the full speed of the machine, and speculative decoding (Lesson 19) makes that speed higher still.</p>
<p>Under load it is wasteful. Lesson 2 showed that a decode step is limited by reading the weights, so a step that served eight sequences would cost little more than one serving a single sequence. Before exploiting that, the next lesson removes work entirely by not prefilling the same prompt twice.</p>
"""),
    ],
    exercises=[
        dict(type="mcq", prompt="<p>Why not run generation directly inside the async route handler?</p>",
             options=["Hummingbird forbids long routes",
                      "It blocks a cooperative-pool thread for the whole generation and lets requests touch the non-thread-safe model concurrently",
                      "Async code cannot use the GPU",
                      "It would be faster, but harder to read"], answer=1,
             explain="<p>Long blocking work starves the cooperative pool, and concurrent forward passes corrupt shared model state.</p>"),
        dict(type="mcq", prompt="<p>Ten requests arrive while the worker is busy. How many times will the worker's <code>wake.wait()</code> return without sleeping once it finishes?</p>",
             options=["Once", "Ten times", "Never", "It depends on the lock"], answer=1,
             explain="<p>Each submit signals the semaphore once, so its count is ten. Each wait consumes one.</p>"),
        dict(type="mcq", prompt="<p>What does a bounded inbox give clients under overload?</p>",
             options=["Faster generation",
                      "An immediate 429 they can act on, instead of an ever-longer wait that ends in a timeout",
                      "Priority for long prompts",
                      "Lower memory use in the model"], answer=1,
             explain="<p>Backpressure turns overload into a fast, explicit signal.</p>"),
        dict(type="multi", prompt="<p>Which objects may HTTP threads touch in this design? Select all that apply.</p>",
             options=["The inbox, under its lock", "A job's cancelled flag", "The model's KV caches",
                      "The PromptFormatter", "The prompt cache"], answer=[0, 1, 3],
             explain="<p>Shared state is limited to locked or thread-safe objects. The caches and the prompt cache belong to the worker alone.</p>"),
    ],
))

# ------------------------------------------------------------------ 14
LESSONS.append(dict(
    part="Part III · The server",
    title="Prompt caching",
    blurb="The second turn of a chat repeats the whole first turn. Keep the caches of recent requests and skip prefilling what the server has already seen, and learn why where you take the snapshot matters as much as how you match it.",
    viz=False,
    goals=[
        "Explain when cached state from one request can be reused by another",
        "Copy caches safely so stored entries are never mutated",
        "Find why naive end-of-reply caching misses for Qwen3.5, and fix it",
        "Measure the effect on time to first token",
    ],
    recap="If an earlier request's tokens are a prefix of a new prompt, its caches already hold the state for that prefix, and only the rest needs prefilling. Store copies, because attention caches are written in place. Matching needs whole-entry prefixes, since linear-attention state cannot be trimmed. And store the snapshot at the last <|im_start|> of the prompt, not at the end of the reply: chat templates re-render past replies differently from how they were generated.",
    sections=[
        dict(title="The opportunity", body="""
<p>A chat client sends the whole conversation every time. Turn 3 of a conversation with a long system prompt contains the system prompt, turn 1, the reply to it, turn 2, the reply to that, and the new message. Without caching, the server prefills all of it again, and time to first token grows with every turn.</p>
<p>But the caches after prefilling a prompt depend only on its tokens. If the server kept the caches from turn 2, turn 3 would only need to prefill what is new. The same works for many requests that share a long system prompt.</p>
"""),
        dict(title="Storing and finding entries", body="""
""" + source("Sources/Inference/PromptCache.swift", "final class PromptCache") + """
<p>Each entry is a token list and the caches that hold exactly those tokens. <code>lookup</code> picks the longest entry whose tokens are a prefix of the new prompt and leaves at least one prompt token to run, because generation needs the logits of the last prompt position. <code>store</code> drops entries that the new one extends and evicts the least recently used entry beyond a fixed capacity (4 by default). A production server would budget by bytes instead of by count, since entries for long prompts can be hundreds of megabytes.</p>
<p>Why whole entries only? With attention caches you could reuse a <em>partial</em> match by trimming the cache back to the common prefix. Qwen3.5's linear-attention layers keep a running state that cannot be rewound to an arbitrary earlier position (Lesson 17). Requiring the whole entry to match works for both kinds of layer.</p>
"""),
        dict(title="Copies, not references", body="""
""" + source("Sources/Inference/PromptCache.swift", "extension KVCache") + """
<p>The KV cache from Lesson 9 writes new keys into its buffer in place. Hand a stored entry's cache to a new request, and that request's generated tokens overwrite the stored state: the next request that matches the entry gets corrupted keys. So <code>lookup</code> returns copies. Slicing out the filled part creates new arrays, and the next update allocates a fresh buffer.</p>
<p>The linear-attention cache needs no deep copy, because its update replaces the state arrays instead of writing into them. Sharing references to arrays nobody mutates is safe. The difference is one of those details that only shows up as a rare, baffling bug if you get it wrong.</p>
"""),
        dict(title="The first attempt missed", body="""
<p>The obvious design stores the caches after each request finishes, covering the prompt and the generated reply, so that the next turn, which starts with exactly that conversation, hits. Implemented that way and tested with a three-turn Qwen3.5 conversation, it hit <strong>zero</strong> times.</p>
<p>The reason is in the chat template. Render the same conversation before and after a turn:</p>
""" + block('''turn 1 prompt:   ...<|im_start|>user\\nWhat is MLX?<|im_end|>\\n<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n
turn 2 prompt:   ...<|im_start|>user\\nWhat is MLX?<|im_end|>\\n<|im_start|>assistant\\nAn array framework.<|im_end|>\\n<|im_start|>user\\n...''', "text") + """
<p>When generating, the prompt ends with an empty think block. When the same reply appears as history in the next turn, the template leaves the think block out. So the tokens the caches hold after turn 1 are <em>not</em> a prefix of turn 2's prompt, and they never will be. Templates that strip reasoning from past turns are common, and even without that, re-tokenizing a reply does not always reproduce the exact tokens that were generated.</p>
"""),
        dict(title="Snapshot where history ends", body="""
<p>The fix is to snapshot the caches at a point the next turn is guaranteed to repeat: the start of the last <code>&lt;|im_start|&gt;</code> in the prompt. Everything before it is earlier turns plus the newest user message, all rendered from history; everything after it is the generation prompt, which changes. The generator already supports this: it ends a prefill chunk exactly at the checkpoint and copies the caches there.</p>
""" + source("Sources/Inference/Generator.swift", "        while rest.count > 1 {", "        pending = MLXArray(rest", include_end=False) + """
<p>The engine picks the checkpoint, prefills from the best cache hit, and stores the snapshot afterwards:</p>
""" + source(ENGINE, "            // Reuse the caches of an earlier request whose tokens are a prefix", "                checkpoint: checkpoint.map { $0 - cached })") + source(ENGINE, "        if let checkpoint, let caches = plain?.checkpointCaches {", "        }") + """
<p>With this change, the same three-turn conversation with a 1,500-token system prompt on Qwen3.5-0.8B:</p>
""" + block('''turn 1: 3.25 s   prompt 1573 tokens, cached    0
turn 2: 0.97 s   prompt 1622 tokens, cached 1566
turn 3: 0.93 s   prompt 1669 tokens, cached 1615''', "text") + """
<p>Each later turn prefills only about 55 new tokens. The cached count appears in the response as <code>usage.prompt_tokens_details.cached_tokens</code>, so clients can see it too.</p>
<div class="note note-warn"><p class="text-sm"><strong>A limitation to know.</strong> The MTP generator of Lesson 19 keeps a second cache for its drafting head, which this prompt cache does not store. So the serial engine uses the prompt cache only when MTP is off (<code>--no-mtp</code>), and MTP requests prefill from scratch. That is a real trade-off: long multi-turn chats favour the prompt cache, short prompts with long answers favour MTP. Extending the cache entries to carry the drafter's cache is a good exercise once you have read Lesson 19.</p></div>
"""),
    ],
    exercises=[
        dict(type="mcq", prompt="<p>Why must <code>lookup</code> return copies of the stored caches?</p>",
             options=["To save memory",
                      "The KV cache writes new tokens into its buffer in place, so the request would overwrite the stored state",
                      "MLX arrays cannot be shared",
                      "Copies are faster to read"], answer=1,
             explain="<p>Without copies, the first request to use an entry corrupts it for every later request.</p>"),
        dict(type="mcq", prompt="<p>Why does caching the state at the end of each reply never hit with Qwen3.5's template?</p>",
             options=["The cache is too small",
                      "The template renders past replies without the empty think block, so the generated token sequence is not a prefix of the next prompt",
                      "Qwen3.5 has no KV cache",
                      "Replies are too long"], answer=1,
             explain="<p>The next prompt differs from the stored tokens right where the reply starts. The fix is to snapshot at a point the template repeats verbatim.</p>"),
        dict(type="numeric", prompt="<p>An entry covers 1,566 tokens and the new prompt has 1,622. How many tokens must be prefilled?</p>",
             answer=56, tolerance=0, placeholder="tokens",
             explain="<p>1,622 − 1,566 = 56. The last of them produces the logits for the first generated token.</p>"),
        dict(type="mcq", prompt="<p>Why does the cache only match whole entries rather than the longest common prefix?</p>",
             options=["It is simpler to code",
                      "Linear-attention state cannot be rewound to an arbitrary earlier position, so a partial match is unusable for Qwen3.5",
                      "Partial matches are always slower",
                      "The tokenizer forbids it"], answer=1,
             explain="<p>Attention caches can be trimmed; a running recurrent state cannot. Whole-entry matching works for both.</p>"),
    ],
))

# ------------------------------------------------------------------ 15
LESSONS.append(dict(
    part="Part III · The server",
    title="Continuous batching",
    blurb="Serve several sequences in each decode step so the weights are read once for all of them. Build a batching engine without padding, then measure how much it really helps on an M1, and why the answer depends on the matmul kernel.",
    viz=True,
    goals=[
        "Explain why batching raises throughput for memory-bound decoding",
        "Build batch views over per-sequence caches for both attention and linear attention",
        "Interleave chunked prefill with batched decode",
        "Read measured batching curves and connect them to kernel behaviour",
        "Explain why batched outputs differ slightly from unbatched ones",
    ],
    recap="A decode step's cost is dominated by reading the weights, so running B sequences in one step multiplies useful work by up to B. The engine keeps each sequence's own caches, stacks the token rows for every matmul, and runs attention per sequence. Linear-attention states are stacked along the batch axis. New prompts are prefilled one chunk per loop. On an M1 the gain is real but limited, because MLX's quantized matmul kernel gets slower per row between 2 and 8 rows; and batching changes rounding enough to flip near-ties.",
    sections=[
        dict(title="Why batching works", body="""
<p>Go back to Lesson 2's table. One sequence decoding at 4 bits does about 4 operations per weight byte, far below the M1's balance point of about 24. The GPU spends most of the step waiting for weights. If eight sequences each need one token, their eight token vectors can be stacked into an 8-row matrix and multiplied by each weight matrix in one pass. The weights are read once, the arithmetic goes up eightfold, and the step should cost little more than a single-sequence step.</p>
<p>"Continuous" means the batch changes all the time. Requests finish at different moments and new ones arrive. Instead of waiting for a whole batch to finish, the engine admits and retires sequences between any two steps.</p>
"""),
        dict(title="Batch views instead of padding", body="""
<p>The hard part is that sequences have different lengths. The common solution is to pad all caches to the longest one and mask the padding. This course uses a simpler design that needs no padding at all:</p>
<ul>
<li><strong>Matmuls run batched.</strong> The new tokens of all sequences form a <code>[B, 1]</code> input, so every projection and MLP sees a <code>[B, 1, hidden]</code> activation. This is where the weight reads, and therefore nearly all of the cost, happen.</li>
<li><strong>Attention runs per sequence.</strong> Each sequence's keys and values stay in its own cache, at its own length, with its own RoPE offset. A <code>BatchKVCache</code> view tells <code>attend</code> to process the rows one at a time:</li>
</ul>
""" + source("Sources/Inference/LayerCache.swift", "final class BatchKVCache") + source("Sources/Inference/LayerCache.swift", "    if let batch = cache as? BatchKVCache {", "        return concatenated(rows, axis: 0)") + """
<p>Qwen3.5's linear-attention layers are even easier, because every sequence's state has the same fixed size. A <code>BatchLinearCache</code> stacks the states along the batch axis for the step and splits the results back:</p>
""" + source("Sources/Inference/LayerCache.swift", "final class BatchLinearCache") + """
<p>The model code needs no other change. A helper builds one view per layer from the per-sequence caches:</p>
""" + source("Sources/Inference/LayerCache.swift", "public func batchCaches") + """
<p>The per-row attention costs a few extra kernel launches per layer. The measurements below show it is small: in bfloat16, going from 4 to 8 rows adds only 7 ms per step.</p>
"""),
        dict(title="The batching engine", body="""
<p>The engine keeps the same inbox and worker thread as the serial engine, but its loop does three things per iteration: admit new jobs, advance at most one prefill chunk, and run one batched decode step for every running sequence.</p>
""" + source("Sources/Inference/BatchEngine.swift", "    private func run()") + source("Sources/Inference/BatchEngine.swift", "    private func prefillChunk(") + source("Sources/Inference/BatchEngine.swift", "    private func decodeStep()") + """
<p><strong>Chunked prefill</strong> is the key scheduling decision. A new 2,000-token prompt prefilled in one go would freeze every running sequence for its whole duration. Prefilling 256 tokens per loop iteration instead, between decode steps, means running sequences slow down while a newcomer is admitted, but never stop. Each sequence samples with its own parameters and its own random key, so a greedy request and a creative one can share a batch.</p>
"""),
        dict(title="What it buys on an M1", body="""
<p>Here is the decode step time for Qwen3.5-0.8B at batch sizes 1 to 8, Release build, base M1:</p>
""" + block('''              B=1        B=2        B=4        B=8
4-bit       11.8 ms    19.0 ms    34.9 ms    63.9 ms     → 85, 105, 115, 125 tok/s total
8-bit       18.5 ms    22.2 ms    31.8 ms    60.3 ms     → 54,  90, 126, 133 tok/s total
bf16        31.5 ms    66.5 ms    69.7 ms    76.5 ms     → 32,  30,  57, 105 tok/s total''', "text") + """
<p>Batching helps, but nowhere near the eightfold the theory suggested, and the shape of the curve depends on the precision. The cause is the matrix multiply kernel, measured in isolation on a 14336×1024 weight:</p>
""" + block('''rows     4-bit       8-bit       bf16
1        142 µs      266 µs      482 µs
2        248 µs      266 µs     1225 µs
4        489 µs      428 µs     1223 µs
8        831 µs      833 µs     1227 µs''', "text") + """
<p>MLX picks a different kernel for one row (a matrix-vector kernel that streams the weights at about 52 GB/s, near the M1's limit) and for several rows. For 4-bit weights on this GPU, the multi-row path's cost grows almost linearly from 2 to 8 rows, so batching barely amortizes anything. For 8-bit weights, two rows cost the same as one. For bfloat16, the first extra row costs 2.5×, but then 8 rows cost the same as 2. The chart below plots the measured curves.</p>
<p>The lesson is not "batching does not work". It is that the benefit is a property of the kernels on your hardware, and you must measure it. On chips with more compute per byte, or with newer MLX kernels, the curve is flatter. Lesson 19 runs into the same table from another direction: speculative decoding is also a multi-row multiply.</p>
""", figure=fig("viz-batching", "Measured throughput versus batch size",
                "Total tokens per second for Qwen3.5-0.8B on a base M1, decode step only. Toggle precisions.")),
        dict(title="Batching changes the numbers", body="""
<p>Running the same eight greedy requests through the serial engine and the batching engine produced identical text for only one of the eight. Is batching broken?</p>
<p>No. The batched test from Lesson 8 shows logits within tolerance at every step. The multi-row kernel accumulates its sums in a different order than the one-row kernel, so values differ in the last bfloat16 digit, and somewhere in 128 tokens a near-tie flips (Lesson 8). After that, the texts diverge. This is called the <strong>batch invariance</strong> problem: a request's output depends on what else is in the batch. It matters if users expect bit-reproducible results with a seed; kernels that are batch-invariant by design exist, at some cost in speed.</p>
"""),
    ],
    exercises=[
        dict(type="mcq", prompt="<p>Why should a decode step for 8 sequences cost much less than 8 single-sequence steps, in principle?</p>",
             options=["Attention is skipped in batches",
                      "The weights, which dominate the step's memory traffic, are read once for all 8",
                      "Batches use a smaller model",
                      "The KV caches are shared"], answer=1,
             explain="<p>Decode is bandwidth-bound on the weights. Stacking rows reuses each weight read.</p>"),
        dict(type="mcq", prompt="<p>How does this engine avoid padding sequences of different lengths?</p>",
             options=["It only batches sequences of equal length",
                      "Matmuls run on stacked rows; attention runs per sequence against each sequence's own cache",
                      "It truncates long sequences",
                      "It pads with zeros and masks"], answer=1,
             explain="<p>The expensive part (weights) is batched; the length-dependent part (attention) stays per sequence.</p>"),
        dict(type="numeric", prompt="<p>From the measured table: with 8-bit weights, how many times higher is total throughput at B=4 than at B=1? (One decimal.)</p>",
             answer=2.3, tolerance=0.05, placeholder="×",
             explain="<p>126 / 54 ≈ 2.33. Far from 4×, but a clear win.</p>"),
        dict(type="mcq", prompt="<p>Why prefill new prompts in 256-token chunks between decode steps?</p>",
             options=["It is faster in total",
                      "So a long new prompt delays the running sequences a little per step instead of freezing them for the whole prefill",
                      "Prefill cannot exceed 256 tokens",
                      "To save cache memory"], answer=1,
             explain="<p>Interleaving trades a bit of the newcomer's time to first token for steady streaming of everyone else.</p>"),
        dict(type="mcq", prompt="<p>A user reports that the same greedy request gives different text depending on server load. What is the most likely cause?</p>",
             options=["A cache corruption bug",
                      "Batch size changes the matmul kernel and its rounding, which can flip a near-tie",
                      "Greedy decoding is random",
                      "The tokenizer is not thread-safe"], answer=1,
             explain="<p>That is the batch invariance problem. Check the logit gap at the first difference, as in Lesson 8.</p>"),
    ],
))
