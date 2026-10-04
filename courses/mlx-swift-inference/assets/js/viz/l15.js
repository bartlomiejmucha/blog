/* Lesson 15 — measured batch throughput on a base M1 (Qwen3.5-0.8B, decode step) */
(function () {
  var V = LC.Viz, C = V.C, el = LC.el;
  var host = document.getElementById("viz-batching");
  if (!host) return;

  var B = [1, 2, 4, 8];
  var SERIES = [
    { name: "4-bit", ms: [11.8, 19.0, 34.9, 63.9], color: C.accent, on: true },
    { name: "8-bit", ms: [18.5, 22.2, 31.8, 60.3], color: C.good, on: true },
    { name: "bf16", ms: [31.5, 66.5, 69.7, 76.5], color: C.warm, on: true }
  ];
  var NS = "http://www.w3.org/2000/svg", W = 640, H = 270, L = 48, R = 16, T = 30, BOT = 34;
  var box = el("div", "space-y-3");
  var toggles = el("div", "flex flex-wrap gap-2");
  var svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 " + W + " " + H); svg.setAttribute("class", "w-full");
  var note = el("p", "font-mono text-xs text-ink-400");
  box.appendChild(toggles); box.appendChild(svg); box.appendChild(note);
  host.appendChild(box);

  SERIES.forEach(function (s) {
    var b = el("button", "btn btn-sm", s.name); b.type = "button";
    b.addEventListener("click", function () { s.on = !s.on; paint(); });
    s.button = b; toggles.appendChild(b);
  });

  function node(tag, a, text) {
    var n = document.createElementNS(NS, tag);
    for (var k in a) n.setAttribute(k, a[k]);
    if (text != null) n.textContent = text;
    svg.appendChild(n); return n;
  }
  function x(i) { return L + i * (W - L - R) / 3; }
  function y(v) { return H - BOT - v / 150 * (H - T - BOT); }

  function paint() {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    [0, 50, 100, 150].forEach(function (v) {
      node("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: C.grid, "stroke-width": 0.6 });
      node("text", { x: L - 6, y: y(v) + 4, "text-anchor": "end", "font-size": 11, fill: C.muted }, v);
    });
    B.forEach(function (b, i) {
      node("text", { x: x(i), y: H - 12, "text-anchor": "middle", "font-size": 11, fill: C.muted }, "B=" + b);
    });
    node("text", { x: 4, y: 14, "font-size": 11, fill: C.muted }, "tok/s total");
    var lines = [];
    SERIES.forEach(function (s) {
      s.button.style.borderColor = s.on ? s.color : "";
      if (!s.on) return;
      var tps = s.ms.map(function (m, i) { return B[i] * 1000 / m; });
      node("polyline", { points: tps.map(function (v, i) { return x(i) + "," + y(v); }).join(" "),
                         fill: "none", stroke: s.color, "stroke-width": 2.5 });
      tps.forEach(function (v, i) { node("circle", { cx: x(i), cy: y(v), r: 4, fill: s.color }); });
      lines.push(s.name + ": " + tps.map(function (v) { return v.toFixed(0); }).join(" → ") + " tok/s (" + (tps[3] / tps[0]).toFixed(1) + "× at B=8)");
    });
    note.textContent = lines.join("   ·   ");
  }
  paint();
})();
