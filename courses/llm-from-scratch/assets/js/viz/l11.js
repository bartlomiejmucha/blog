/* Lesson 11 — KV cache simulator + size calculator */
(function () {
  var V = LC.Viz, el = LC.el;

  var c = document.getElementById("viz-kvcache");
  if (c) {
    var promptLen = 6, gen = 0, cacheOn = true;
    var box = el("div", "space-y-3");
    var row = el("div", "flex min-h-[3rem] flex-wrap gap-1 rounded-lg border border-ink-700 bg-ink-850 p-3");
    var stats = el("div", "grid gap-2 sm:grid-cols-2 font-mono text-xs");
    var ctr = el("div", "flex flex-wrap gap-2");
    var step = el("button", "btn btn-sm btn-primary", "Generate a token");
    var reset = el("button", "btn btn-sm", "Reset");
    var tog = el("button", "btn btn-sm", "Cache: on");
    [step, reset, tog].forEach(function (b) { b.type = "button"; ctr.appendChild(b); });
    var note = el("p", "text-xs text-ink-400");
    box.appendChild(row); box.appendChild(stats); box.appendChild(ctr); box.appendChild(note);
    c.appendChild(box);

    function work() {
      // Positions whose K/V were computed by the step that produced the most
      // recent token. Without the cache that pass re-ran over everything that
      // existed before it, i.e. the prompt plus the tokens already generated.
      return cacheOn ? 1 : promptLen + gen - 1;
    }
    function totalWork() {
      var t = promptLen; // prefill
      for (var i = 0; i < gen; i++) t += cacheOn ? 1 : promptLen + i;
      return t;
    }
    function draw() {
      row.innerHTML = "";
      for (var i = 0; i < promptLen + gen; i++) {
        var isNew = i === promptLen + gen - 1 && gen > 0;
        var cached = cacheOn && !isNew;
        var t = el("span", "tok " + (isNew ? "border-accent bg-accent/25 text-ink-100"
          : cached ? "border-good/50 bg-good/10 text-good" : "border-warm/50 bg-warm/10 text-warm"),
          (i < promptLen ? "p" : "g") + i);
        t.title = cached ? "K/V read from cache" : "K/V computed this step";
        row.appendChild(t);
      }
      stats.innerHTML =
        "<p class='text-ink-400'>tokens generated: <span class='text-ink-100'>" + gen + "</span></p>" +
        "<p class='text-ink-400'>positions processed this step: <span class='" + (cacheOn ? "text-good" : "text-bad") + "'>" + (gen ? work() : promptLen) + "</span></p>" +
        "<p class='text-ink-400'>cumulative position-passes: <span class='text-ink-100'>" + totalWork() + "</span></p>" +
        "<p class='text-ink-400'>cache entries held: <span class='text-accent'>" + (cacheOn ? promptLen + gen : 0) + "</span></p>";
      note.textContent = cacheOn
        ? "Green = K/V reused from cache. Each new token costs one position's worth of work, plus attention against the whole cache."
        : "Cache off: every step recomputes every position from scratch. Cumulative work grows quadratically — compare the number above with the cache on.";
    }
    step.addEventListener("click", function () { gen++; draw(); });
    reset.addEventListener("click", function () { gen = 0; draw(); });
    tog.addEventListener("click", function () {
      cacheOn = !cacheOn;
      tog.textContent = "Cache: " + (cacheOn ? "on" : "off");
      tog.classList.toggle("btn-primary", !cacheOn);
      draw();
    });
    draw();
  }

  var cs = document.getElementById("viz-cachesize");
  if (cs) {
    var layers = 80, kvh = 64, dh = 128, seq = 8192, bits = 16, batch = 1;
    var box2 = el("div", "grid gap-4 sm:grid-cols-2");
    var ctrl = el("div", "space-y-3"), out = el("div", "");
    box2.appendChild(ctrl); box2.appendChild(out);
    cs.appendChild(box2);

    function sel(label, opts, val, cb) {
      var w = el("div", "space-y-1");
      w.appendChild(el("p", "text-xs text-ink-400", label));
      var s = document.createElement("select"); s.className = "field";
      opts.forEach(function (o) { var n = document.createElement("option"); n.value = o[1]; n.textContent = o[0]; s.appendChild(n); });
      s.value = val;
      s.addEventListener("change", function () { cb(parseFloat(s.value)); });
      w.appendChild(s); return w;
    }
    ctrl.appendChild(sel("layers", [["32", 32], ["48", 48], ["80", 80], ["126", 126]], layers, function (v) { layers = v; draw2(); }));
    ctrl.appendChild(sel("KV heads", [["8 (GQA)", 8], ["16", 16], ["32", 32], ["64 (full MHA)", 64]], kvh, function (v) { kvh = v; draw2(); }));
    ctrl.appendChild(sel("sequence length", [["2k", 2048], ["8k", 8192], ["32k", 32768], ["128k", 131072]], seq, function (v) { seq = v; draw2(); }));
    ctrl.appendChild(sel("precision", [["fp16 (2 bytes)", 16], ["int8 (1 byte)", 8], ["int4 (0.5 bytes)", 4]], bits, function (v) { bits = v; draw2(); }));
    ctrl.appendChild(sel("concurrent sequences", [["1", 1], ["8", 8], ["32", 32], ["128", 128]], batch, function (v) { batch = v; draw2(); }));

    function draw2() {
      var bytes = 2 * layers * kvh * dh * seq * (bits / 8) * batch;
      var gb = bytes / 1e9;
      var full = 2 * layers * 64 * dh * seq * 2 * batch / 1e9;
      out.innerHTML =
        "<div class='rounded-lg border border-ink-700 bg-ink-850 p-3 font-mono text-xs space-y-1.5'>" +
        "<p class='text-ink-400'>2 × layers × kv_heads × d_head × seq × bytes × batch</p>" +
        "<p class='text-ink-300'>2 × " + layers + " × " + kvh + " × " + dh + " × " + seq + " × " + (bits / 8) + " × " + batch + "</p>" +
        "<hr class='border-ink-700'>" +
        "<p class='text-2xl " + (gb > 80 ? "text-bad" : gb > 20 ? "text-warm" : "text-good") + "'>" + gb.toFixed(1) + " GB</p>" +
        "<p class='text-ink-400'>versus " + full.toFixed(1) + " GB at full MHA / fp16</p></div>" +
        "<p class='mt-2 text-xs text-ink-400'>" +
        (gb > 80 ? "This exceeds a single 80 GB GPU on its own, before any model weights. This is the regime where GQA, paged attention and cache quantization stop being optional."
          : "Compare against ~140 GB of fp16 weights for a 70B model — the cache is a substantial fraction of serving memory, and it scales with every concurrent user.") + "</p>";
    }
    draw2();
  }
})();
