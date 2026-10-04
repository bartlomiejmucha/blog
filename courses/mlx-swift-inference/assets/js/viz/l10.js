/* Lesson 10 — temperature, top-k, top-p, min-p on a toy distribution */
(function () {
  var V = LC.Viz, C = V.C, el = LC.el;
  var host = document.getElementById("viz-sampling");
  if (!host) return;

  var TOKENS = [" blue", " clear", " bright", " grey", " dark", " cloudy", " beautiful", " red", " vast", " empty", " green", " loud"];
  var LOGITS = [5.1, 3.9, 3.3, 3.0, 2.6, 2.4, 1.9, 1.2, 1.0, 0.4, -0.5, -1.4];

  var box = el("div", "space-y-3");
  var controls = el("div", "grid gap-3 sm:grid-cols-2");
  function slider(label, min, max, step, value) {
    var w = el("label", "space-y-1 text-xs text-ink-400");
    var l = el("span", ""); var s = document.createElement("input");
    s.type = "range"; s.className = "slider"; s.min = min; s.max = max; s.step = step; s.value = value;
    w.appendChild(l); w.appendChild(s); controls.appendChild(w);
    return { s: s, l: l, label: label };
  }
  var T = slider("temperature", 0.1, 2, 0.05, 1);
  var K = slider("top-k (0 = off)", 0, 12, 1, 0);
  var P = slider("top-p (1 = off)", 0.05, 1, 0.01, 1);
  var M = slider("min-p (0 = off)", 0, 0.5, 0.01, 0);
  var bars = el("div", "space-y-1.5");
  var note = el("p", "font-mono text-xs text-ink-400");
  box.appendChild(controls); box.appendChild(bars); box.appendChild(note);
  host.appendChild(box);

  function paint() {
    var t = +T.s.value, k = +K.s.value, p = +P.s.value, mp = +M.s.value;
    T.l.textContent = "temperature " + t.toFixed(2); K.l.textContent = "top-k " + (k || "off");
    P.l.textContent = "top-p " + (p >= 1 ? "off" : p.toFixed(2)); M.l.textContent = "min-p " + (mp ? mp.toFixed(2) : "off");
    var probs = V.softmax(LOGITS, t);          // already in descending order
    var keep = probs.map(function () { return true; });
    if (k > 0) keep = keep.map(function (x, i) { return x && i < k; });
    if (mp > 0) keep = keep.map(function (x, i) { return x && probs[i] >= mp * probs[0]; });
    if (p < 1) { var before = 0; keep = keep.map(function (x, i) { var ok = before < p; before += probs[i]; return x && ok; }); }
    var total = 0; probs.forEach(function (q, i) { if (keep[i]) total += q; });
    bars.innerHTML = "";
    probs.forEach(function (q, i) {
      var row = el("div", "flex items-center gap-2" + (keep[i] ? "" : " opacity-30"));
      row.appendChild(el("code", "w-24 shrink-0 text-right text-xs text-ink-300", TOKENS[i]));
      var tr = el("div", "h-4 flex-1 overflow-hidden rounded bg-ink-800");
      var f = el("div", "h-full"); var shown = keep[i] ? q / total : q;
      f.style.width = Math.max(0.5, shown * 100) + "%"; f.style.background = keep[i] ? C.accent : C.line;
      tr.appendChild(f); row.appendChild(tr);
      row.appendChild(el("span", "w-14 text-right font-mono text-xs text-ink-400", (shown * 100).toFixed(1) + "%"));
      bars.appendChild(row);
    });
    var n = keep.filter(Boolean).length;
    note.textContent = n + " of " + TOKENS.length + " tokens kept; kept mass before renormalizing " + (total * 100).toFixed(1) + "%.";
  }
  [T, K, P, M].forEach(function (c) { c.s.addEventListener("input", paint); });
  paint();
})();
