/* Lesson 13 — scaling curve, chinchilla frontier, compute estimator */
(function () {
  var C = LC.Viz.C;
  var V = LC.Viz, el = LC.el;

  var s = document.getElementById("viz-scaling");
  if (s) {
    var W = 460, H = 220;
    function L(C) { return 1.7 + 12 * Math.pow(C, -0.055); }
    var box = el("div", "space-y-2");
    var svgw = el("div", "");
    var note = el("p", "text-xs text-ink-400");
    box.appendChild(svgw); box.appendChild(note);
    s.appendChild(box);

    var lin = [], log = [];
    for (var e = 18; e <= 26; e += 0.05) {
      var flops = Math.pow(10, e), l = L(flops);   // not C: that is the shared palette
      var x = 30 + (e - 18) / 8 * (W / 2 - 50);
      lin.push(x + "," + (H - 25 - (4.2 - l) / 2.6 * (H - 50)));
      log.push((W / 2 + 30 + (e - 18) / 8 * (W / 2 - 50)) + "," + (H - 25 - (Math.log(4.2) - Math.log(l)) / 0.9 * (H - 50)));
    }
    svgw.innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" class="w-full">' +
      '<polyline points="' + lin.join(" ") + '" fill="none" stroke="' + C.accent + '" stroke-width="2"/>' +
      '<polyline points="' + log.join(" ") + '" fill="none" stroke="' + C.good + '" stroke-width="2"/>' +
      '<text x="30" y="16" font-size="10" fill="' + C.accent + '" font-family="monospace">loss vs log(compute)</text>' +
      '<text x="' + (W / 2 + 30) + '" y="16" font-size="10" fill="' + C.good + '" font-family="monospace">log(loss) vs log(compute) — a straight line</text>' +
      '<line x1="20" y1="' + (H - 25) + '" x2="' + (W / 2 - 10) + '" y2="' + (H - 25) + '" stroke="' + C.grid + '"/>' +
      '<line x1="' + (W / 2 + 20) + '" y1="' + (H - 25) + '" x2="' + (W - 10) + '" y2="' + (H - 25) + '" stroke="' + C.grid + '"/></svg>';
    note.textContent = "The same data on two axes. The straight line on log-log axes is what 'power law' means, and it is what makes the loss of a much larger run predictable in advance.";
  }

  var ch = document.getElementById("viz-chinchilla");
  if (ch) {
    // Parameterised by tokens-per-parameter, the quantity the lesson is about.
    // C = 6ND with D = ratio*N gives N = sqrt(C / (6*ratio)).
    var logRatio = Math.log10(20);
    var budget = 1e22;
    var box2 = el("div", "space-y-3");
    var head = el("div", "flex flex-wrap items-center gap-3");
    var inp = document.createElement("input");
    inp.type = "range"; inp.min = 0; inp.max = 3.3; inp.step = 0.02; inp.value = logRatio; inp.className = "slider max-w-xs";
    head.appendChild(el("span", "text-xs text-ink-400", "more parameters ← → more data"));
    head.appendChild(inp);
    var out = el("div", "rounded-lg border border-ink-700 bg-ink-850 p-3 font-mono text-xs space-y-1");
    var bar = el("div", "bar-track");
    var fill = el("div", "bar-fill");
    bar.appendChild(fill);
    var note2 = el("p", "text-xs text-ink-400");
    box2.appendChild(head); box2.appendChild(out); box2.appendChild(bar); box2.appendChild(note2);
    ch.appendChild(box2);

    function draw() {
      logRatio = parseFloat(inp.value);
      var ratio = Math.pow(10, logRatio);
      var N = Math.sqrt(budget / (6 * ratio));
      var D = ratio * N;
      // loss model: penalise deviation from 20 tokens/param
      var dev = Math.abs(Math.log10(ratio / 20));
      var loss = 1.95 + 0.55 * dev * dev;
      out.innerHTML =
        "<p class='text-ink-400'>compute budget fixed at 10²² FLOPs</p>" +
        "<p>parameters N = <span class='text-accent'>" + (N / 1e9).toFixed(2) + "B</span></p>" +
        "<p>training tokens D = <span class='text-warm'>" + (D / 1e9).toFixed(D < 1e11 ? 1 : 0) + "B</span></p>" +
        "<p>tokens per parameter = <span class='text-ink-100'>" + ratio.toFixed(1) + "</span></p>" +
        "<p class='text-ink-100'>estimated loss ≈ " + loss.toFixed(3) + "</p>";
      var quality = Math.max(0, 1 - dev);
      fill.style.width = (quality * 100) + "%";
      fill.style.background = dev < 0.15 ? "var(--color-good)" : dev < 0.5 ? "var(--color-warm)" : "var(--color-bad)";
      note2.textContent = ratio < 5 ? "Far too large for the data — this is the GPT-3 mistake: enormous parameter count, undertrained."
        : ratio > 80 ? "Heavily overtrained relative to compute-optimal. Worse loss for this training budget, but a smaller and permanently cheaper model to serve — often the right call in production."
          : "Near the Chinchilla-optimal ratio of roughly 20 tokens per parameter. This is where loss is minimised for a fixed training budget.";
    }
    inp.addEventListener("input", draw);
    draw();
  }

  var fl = document.getElementById("viz-flops");
  if (fl) {
    var N = 7, D = 2000; // billions
    var box3 = el("div", "grid gap-4 sm:grid-cols-2");
    var ctrl = el("div", "space-y-3"), out3 = el("div", "");
    box3.appendChild(ctrl); box3.appendChild(out3);
    fl.appendChild(box3);
    function sl(label, min, max, step, val, cb, unit) {
      var w = el("div", "space-y-1");
      var t = el("div", "flex justify-between text-xs");
      t.appendChild(el("span", "text-ink-400", label));
      var o = el("span", "font-mono text-accent", val + unit);
      t.appendChild(o);
      var i = document.createElement("input");
      i.type = "range"; i.min = min; i.max = max; i.step = step; i.value = val; i.className = "slider";
      i.addEventListener("input", function () { o.textContent = i.value + unit; cb(parseFloat(i.value)); });
      w.appendChild(t); w.appendChild(i); return w;
    }
    ctrl.appendChild(sl("parameters", 1, 500, 1, N, function (v) { N = v; draw3(); }, "B"));
    ctrl.appendChild(sl("training tokens", 100, 20000, 100, D, function (v) { D = v; draw3(); }, "B"));

    function draw3() {
      var C = 6 * N * 1e9 * D * 1e9;
      var gpuFlops = 4e14 * 0.4; // H100 bf16 with realistic MFU
      var gpuSeconds = C / gpuFlops;
      var gpuDays = gpuSeconds / 86400;
      var cost = gpuDays * 24 * 2.5;
      out3.innerHTML = "<div class='rounded-lg border border-ink-700 bg-ink-850 p-3 font-mono text-xs space-y-1.5'>" +
        "<p class='text-ink-400'>C = 6 × N × D</p>" +
        "<p class='text-ink-100'>= " + C.toExponential(2) + " FLOPs</p>" +
        "<hr class='border-ink-700'>" +
        "<p>≈ " + Math.round(gpuDays).toLocaleString() + " GPU-days</p>" +
        "<p>≈ " + (gpuDays / 1000).toFixed(1) + " days on 1,000 GPUs</p>" +
        "<p class='text-warm'>≈ $" + (cost / 1e6).toFixed(2) + "M at $2.50/GPU-hour</p>" +
        "<hr class='border-ink-700'>" +
        "<p class='text-ink-400'>tokens per parameter: " + (D / N).toFixed(0) + "</p>" +
        "<p class='text-ink-400'>inference: " + (2 * N).toFixed(0) + " GFLOPs per generated token</p></div>" +
        "<p class='mt-2 text-xs text-ink-400'>Rough figures assuming 40% hardware utilisation — real runs vary widely, but the order of magnitude is right.</p>";
    }
    draw3();
  }
})();
