/* Lesson 5 — one group of 64 weights quantized to 4 bits */
(function () {
  var V = LC.Viz, C = V.C, el = LC.el;
  var host = document.getElementById("viz-quant");
  if (!host) return;

  // Deterministic, roughly normal weights (std 0.05).
  var seed = 7;
  function rnd() { seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
  var base = [];
  for (var i = 0; i < 64; i++) {
    var u = rnd(), v = rnd();
    base.push(0.05 * Math.sqrt(-2 * Math.log(u + 1e-9)) * Math.cos(2 * Math.PI * v));
  }

  var NS = "http://www.w3.org/2000/svg";
  var W = 640, H = 220, pad = 30;
  var box = el("div", "space-y-3");
  var head = el("div", "flex flex-wrap items-center gap-3");
  var slider = document.createElement("input");
  slider.type = "range"; slider.className = "slider max-w-xs"; slider.min = -0.1; slider.max = 0.6; slider.step = 0.005; slider.value = 0.1;
  var lab = el("span", "font-mono text-sm text-accent", "");
  head.appendChild(el("span", "text-xs text-ink-400", "outlier value")); head.appendChild(slider); head.appendChild(lab);
  var svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 " + W + " " + H); svg.setAttribute("class", "w-full");
  var stats = el("p", "font-mono text-xs text-ink-300");
  box.appendChild(head); box.appendChild(svg); box.appendChild(stats);
  host.appendChild(box);

  function node(tag, attrs) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    svg.appendChild(n); return n;
  }

  function paint() {
    var w = base.slice(); w[0] = parseFloat(slider.value);
    lab.textContent = w[0].toFixed(3);
    var lo = Math.min.apply(null, w), hi = Math.max.apply(null, w);
    var scale = (hi - lo) / 15, bias = lo;
    var q = w.map(function (x) { return scale ? Math.round((x - bias) / scale) : 0; });
    var r = q.map(function (k) { return scale * k + bias; });
    var err = 0, errRest = 0;
    w.forEach(function (x, i) { var e = Math.abs(x - r[i]); err += e; if (i > 0) errRest += e; });

    while (svg.firstChild) svg.removeChild(svg.firstChild);
    // Fit the axis to the data, with a margin, so the group fills the plot.
    var span = hi - lo, y0 = lo - 0.08 * span, y1 = hi + 0.08 * span;
    function y(v) { return H - pad - (v - y0) / (y1 - y0) * (H - 2 * pad); }
    function x(i) { return pad + i * (W - 2 * pad) / 63; }
    for (var k = 0; k <= 15; k++) {
      node("line", { x1: pad, x2: W - pad, y1: y(bias + k * scale), y2: y(bias + k * scale), stroke: C.grid, "stroke-width": 0.6 });
    }
    w.forEach(function (v, i) {
      node("line", { x1: x(i), x2: x(i), y1: y(v), y2: y(r[i]), stroke: C.line, "stroke-width": 1 });
      node("circle", { cx: x(i), cy: y(r[i]), r: 2.2, fill: C.accent });
      node("circle", { cx: x(i), cy: y(v), r: i === 0 ? 5 : 3.5, fill: "none",
                       stroke: i === 0 ? C.warm : C.muted, "stroke-width": 1.4 });
    });
    node("text", { x: W - pad, y: y(hi) - 6, "text-anchor": "end", "font-size": 11, fill: C.muted }, "max " + hi.toFixed(3));
    node("text", { x: W - pad, y: y(lo) + 14, "text-anchor": "end", "font-size": 11, fill: C.muted }, "min " + lo.toFixed(3));
    stats.textContent = "16 levels (lines) · scale " + scale.toFixed(4) + " · max error " + (scale / 2).toFixed(4) +
      " · mean error of the other 63 weights " + (errRest / 63).toFixed(4);
  }
  slider.addEventListener("input", paint);
  paint();
})();
