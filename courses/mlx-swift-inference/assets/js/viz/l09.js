/* Lesson 9 — KV cache memory versus context length */
(function () {
  var V = LC.Viz, C = V.C, el = LC.el;
  var host = document.getElementById("viz-kvcache");
  if (!host) return;

  // Per-token KV bytes and fixed state bytes, bf16 cache.
  var MODELS = [
    { name: "Qwen3-0.6B", perToken: 28 * 2 * 8 * 128 * 2, fixed: 0, weights: 0.35e9 },
    { name: "Qwen3.5-0.8B", perToken: 6 * 2 * 2 * 256 * 2,
      // 18 Gated DeltaNet layers: 16 heads x 128 x 128 float32 state + 3 x 6144 bf16 conv window
      fixed: 18 * (16 * 128 * 128 * 4 + 3 * 6144 * 2), weights: 0.45e9 }
  ];
  var box = el("div", "space-y-3");
  var head = el("div", "flex flex-wrap items-center gap-3");
  var slider = document.createElement("input");
  slider.type = "range"; slider.className = "slider max-w-sm"; slider.min = 0; slider.max = 100; slider.value = 40;
  var lab = el("span", "font-mono text-sm text-accent");
  head.appendChild(el("span", "text-xs text-ink-400", "context")); head.appendChild(slider); head.appendChild(lab);
  box.appendChild(head);
  var rows = MODELS.map(function (m) {
    var r = el("div", "space-y-1");
    var t = el("div", "flex justify-between text-xs"); var n = el("span", "text-ink-100", m.name); var v = el("span", "font-mono text-ink-300");
    t.appendChild(n); t.appendChild(v);
    var track = el("div", "bar-track h-3"); var fill = el("div", "bar-fill"); track.appendChild(fill);
    r.appendChild(t); r.appendChild(track); box.appendChild(r);
    return { m: m, v: v, fill: fill };
  });
  var note = el("p", "text-xs text-ink-400");
  box.appendChild(note);
  host.appendChild(box);

  function tokens() { return Math.round(256 * Math.pow(131072 / 256, slider.value / 100)); }
  function fmt(b) { return b >= 1e9 ? (b / 1e9).toFixed(2) + " GB" : (b / 1e6).toFixed(0) + " MB"; }
  function paint() {
    var n = tokens();
    lab.textContent = n.toLocaleString() + " tokens";
    var maxB = MODELS[0].perToken * 131072;
    rows.forEach(function (r) {
      var b = r.m.perToken * n + r.m.fixed;
      r.v.textContent = fmt(b) + " cache (weights at 4 bits ≈ " + fmt(r.m.weights) + ")";
      r.fill.style.width = Math.max(0.5, 100 * b / maxB) + "%";
      r.fill.style.background = b > r.m.weights ? C.warm : C.accent;
    });
    note.textContent = "Bars turn orange once the cache is larger than the weights. Qwen3: " +
      (MODELS[0].perToken / 1024).toFixed(0) + " KB per token. Qwen3.5: " + (MODELS[1].perToken / 1024).toFixed(0) +
      " KB per token plus a fixed " + fmt(MODELS[1].fixed) + " of recurrent state.";
  }
  slider.addEventListener("input", paint);
  paint();
})();
