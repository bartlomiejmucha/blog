/* Lesson 17 — quantization grid, LoRA calculator, MoE routing */
(function () {
  var V = LC.Viz, el = LC.el;

  var q = document.getElementById("viz-quant");
  if (q) {
    var bits = 4;
    // A small LCG, not i*constant%1000: that is an arithmetic sequence and renders
    // as a repeating ramp rather than anything resembling a weight distribution.
    var WEIGHTS = [], seed = 20240617;
    for (var i = 0; i < 48; i++) {
      seed = (seed * 1103515245 + 12345) % 2147483648;
      var v = (seed / 2147483648 - 0.5) * 2;
      WEIGHTS.push(Math.sign(v) * Math.pow(Math.abs(v), 1.8));
    }
    // One genuine outlier channel, set after the curve so it really is the
    // largest magnitude present - it is what sets the quantisation scale.
    WEIGHTS[7] = 2.6;
    var box = el("div", "space-y-3");
    var ctr = el("div", "flex flex-wrap gap-2");
    var grid = el("div", "space-y-1.5");
    var stat = el("div", "rounded-lg border border-ink-700 bg-ink-850 p-3 font-mono text-xs space-y-1");
    box.appendChild(ctr); box.appendChild(grid); box.appendChild(stat);
    q.appendChild(box);

    [16, 8, 4, 2].forEach(function (b) {
      var btn = el("button", "btn btn-sm" + (b === bits ? " btn-primary" : ""), b + "-bit"); btn.type = "button";
      btn.addEventListener("click", function () {
        bits = b;
        LC.$$("button", ctr).forEach(function (n) { n.classList.remove("btn-primary"); });
        btn.classList.add("btn-primary"); draw();
      });
      ctr.appendChild(btn);
    });

    function draw() {
      var levels = bits >= 16 ? 65536 : Math.pow(2, bits);
      var max = Math.max.apply(null, WEIGHTS.map(Math.abs));
      var stepSize = 2 * max / (levels - 1);
      var err = 0;
      grid.innerHTML = "";
      var row = el("div", "flex flex-wrap gap-[3px]");
      WEIGHTS.forEach(function (w) {
        var qv = Math.round(w / stepSize) * stepSize;
        err += Math.abs(w - qv);
        var d = el("div", "h-5 w-5 rounded-[3px]");
        d.style.background = V.heat((qv + max) / (2 * max));
        d.title = "original " + w.toFixed(4) + " → stored " + qv.toFixed(4);
        row.appendChild(d);
      });
      grid.appendChild(row);
      stat.innerHTML =
        "<p class='text-ink-400'>representable levels: <span class='text-ink-100'>" + levels.toLocaleString() + "</span></p>" +
        "<p class='text-ink-400'>step between levels: <span class='text-ink-100'>" + stepSize.toFixed(5) + "</span></p>" +
        "<p class='text-ink-400'>mean absolute error: <span class='" + (err / WEIGHTS.length > 0.05 ? "text-bad" : "text-good") + "'>" +
        (err / WEIGHTS.length).toFixed(5) + "</span></p>" +
        "<p class='text-ink-400'>bytes for a 7B model: <span class='text-accent'>" + (7e9 * bits / 8 / 1e9).toFixed(1) + " GB</span></p>" +
        "<p class='text-ink-600'>" + (bits <= 2
          ? "At 2 bits nearly all distinctions collapse — quality falls apart without much more sophisticated schemes."
          : "Note the one large outlier weight: because the scale is set by the maximum, a single extreme value coarsens the grid for every other weight. That is why modern methods use per-block scales and handle outlier channels separately.") + "</p>";
    }
    draw();
  }

  var lo = document.getElementById("viz-lora");
  if (lo) {
    var d = 4096, r = 8;
    var box2 = el("div", "grid gap-4 sm:grid-cols-2");
    var ctrl = el("div", "space-y-3"), out = el("div", "");
    box2.appendChild(ctrl); box2.appendChild(out);
    lo.appendChild(box2);
    function sel(label, opts, val, cb) {
      var w = el("div", "space-y-1");
      w.appendChild(el("p", "text-xs text-ink-400", label));
      var s = document.createElement("select"); s.className = "field";
      opts.forEach(function (o) { var n = document.createElement("option"); n.value = n.textContent = o; s.appendChild(n); });
      s.value = val;
      s.addEventListener("change", function () { cb(parseInt(s.value, 10)); });
      w.appendChild(s); return w;
    }
    ctrl.appendChild(sel("matrix dimension d", [768, 1024, 2048, 4096, 8192], d, function (v) { d = v; draw2(); }));
    ctrl.appendChild(sel("LoRA rank r", [1, 2, 4, 8, 16, 32, 64, 128], r, function (v) { r = v; draw2(); }));

    function draw2() {
      var full = d * d, lora = 2 * d * r;
      out.innerHTML = "<div class='rounded-lg border border-ink-700 bg-ink-850 p-3 font-mono text-xs space-y-1.5'>" +
        "<p class='text-ink-400'>full matrix W: [" + d + " × " + d + "]</p>" +
        "<p class='text-ink-100'>" + full.toLocaleString() + " trainable parameters</p>" +
        "<hr class='border-ink-700'>" +
        "<p class='text-ink-400'>B: [" + d + " × " + r + "]  A: [" + r + " × " + d + "]</p>" +
        "<p class='text-good'>" + lora.toLocaleString() + " trainable parameters</p>" +
        "<p class='text-accent'>" + (lora / full * 100).toFixed(2) + "% of full fine-tuning</p>" +
        "<p class='text-ink-400'>adapter size at fp16: " + (lora * 2 / 1e6).toFixed(2) + " MB</p></div>" +
        "<p class='mt-2 text-xs text-ink-400'>" + (r >= 64
          ? "High rank approaches full fine-tuning in both capacity and cost. Most tasks do not need it."
          : "Rank 8–16 is the usual sweet spot for style and behaviour adaptation. After training, BA can be folded into W so inference costs nothing extra.") + "</p>";
    }
    draw2();
  }

  var mo = document.getElementById("viz-moe");
  if (mo) {
    var nExp = 8, topk = 2;
    var TOKENS = ["def", " calculate", "(", "x", ")", ":", " return", " x", " *", " 2", " The", " weather", " in", " Paris", " is", " mild"];
    var counts = new Array(nExp).fill(0);
    var box3 = el("div", "space-y-3");
    var flow = el("div", "space-y-1.5");
    var bars = el("div", "space-y-1");
    var ctr3 = el("div", "flex gap-2");
    var send = el("button", "btn btn-sm btn-primary", "Send next token"); send.type = "button";
    var rst = el("button", "btn btn-sm", "Reset"); rst.type = "button";
    ctr3.appendChild(send); ctr3.appendChild(rst);
    var note = el("p", "text-xs text-ink-400");
    box3.appendChild(flow); box3.appendChild(ctr3); box3.appendChild(bars); box3.appendChild(note);
    mo.appendChild(box3);

    var i = 0;
    function route(tok) {
      var h = 0;
      for (var k = 0; k < tok.length; k++) h = (h * 31 + tok.charCodeAt(k)) >>> 0;
      var scores = [];
      for (var e = 0; e < nExp; e++) scores.push(((h * (e + 7) % 1000) / 1000));
      var order = scores.map(function (s, e) { return [s, e]; }).sort(function (a, b) { return b[0] - a[0]; });
      return order.slice(0, topk).map(function (o) { return o[1]; });
    }
    function draw3() {
      flow.innerHTML = "";
      for (var k = 0; k <= Math.min(i, TOKENS.length - 1); k++) {
        var chosen = route(TOKENS[k]);
        var row = el("div", "flex items-center gap-2 " + (k === i ? "" : "opacity-40"));
        row.appendChild(el("code", "w-24 shrink-0 truncate rounded bg-ink-800 px-1.5 py-0.5 text-right text-xs text-ink-100", TOKENS[k].replace(/ /g, "␣")));
        var ex = el("div", "flex gap-1");
        for (var e = 0; e < nExp; e++) {
          var on = chosen.indexOf(e) !== -1;
          var d2 = el("div", "flex h-5 w-5 items-center justify-center rounded text-[9px] font-mono " +
            (on ? "bg-accent/40 text-ink-100 border border-accent" : "bg-ink-800 text-ink-600"), "E" + e);
          ex.appendChild(d2);
        }
        row.appendChild(ex);
        flow.appendChild(row);
      }
      counts = new Array(nExp).fill(0);
      for (var k2 = 0; k2 <= Math.min(i, TOKENS.length - 1); k2++)
        route(TOKENS[k2]).forEach(function (e) { counts[e]++; });
      var mx = Math.max.apply(null, counts) || 1;
      bars.innerHTML = "<p class='text-xs font-semibold text-ink-100'>Expert load</p>" +
        counts.map(function (c, e) {
          return "<div class='flex items-center gap-2'><code class='w-8 text-xs text-ink-400'>E" + e + "</code>" +
            "<div class='h-2 flex-1 rounded bg-ink-800'><div class='h-full rounded' style='width:" + (c / mx * 100) +
            "%;background:" + V.heat(c / mx) + "'></div></div><span class='w-6 text-right font-mono text-xs text-ink-400'>" + c + "</span></div>";
        }).join("");
      note.textContent = "Each token activates " + topk + " of " + nExp + " experts, so per-token compute is roughly " +
        (topk / nExp * 100).toFixed(0) + "% of the dense equivalent — while all " + nExp +
        " experts must still be held in memory. Uneven bars are why training needs an explicit load-balancing loss.";
      send.disabled = i >= TOKENS.length - 1;
    }
    send.addEventListener("click", function () { if (i < TOKENS.length - 1) i++; draw3(); });
    rst.addEventListener("click", function () { i = 0; draw3(); });
    draw3();
  }
})();
