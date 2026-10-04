/* Lesson 18 — speculative decoding speed-up model, with measured M1 points */
(function () {
  var V = LC.Viz, C = V.C, el = LC.el;
  var host = document.getElementById("viz-speculative");
  if (!host) return;

  // Measured on a base M1, Qwen3.5-0.8B (Lesson 19). Draft cost = 3 ms / 1-token step.
  var PRESETS = [
    { name: "M1 4-bit", a: 0.87, cv: 16.8 / 12.2, cd: 3 / 12.2, measured: 0.94 },
    { name: "M1 8-bit", a: 0.92, cv: 18.6 / 18.6, cd: 3 / 18.6, measured: 1.31 },
    { name: "M1 bf16", a: 0.92, cv: 65.0 / 30.1, cd: 3 / 30.1, measured: 0.78 }
  ];

  var box = el("div", "space-y-4");
  var presets = el("div", "flex flex-wrap gap-2");
  var controls = el("div", "grid gap-3 sm:grid-cols-3");
  function slider(min, max, step, value) {
    var w = el("label", "space-y-1 text-xs text-ink-400"); var l = el("span", "");
    var s = document.createElement("input"); s.type = "range"; s.className = "slider";
    s.min = min; s.max = max; s.step = step; s.value = value;
    w.appendChild(l); w.appendChild(s); controls.appendChild(w);
    return { s: s, l: l };
  }
  var A = slider(0.3, 1, 0.01, 0.9), CV = slider(0.9, 2.5, 0.01, 1.0), CD = slider(0, 0.5, 0.01, 0.15);
  var big = el("p", "font-mono text-2xl text-ink-100");
  var track = el("div", "relative h-3 rounded-full bg-ink-800");
  var fill = el("div", "absolute left-0 top-0 h-3 rounded-full"); track.appendChild(fill);
  var mark = el("div", "absolute top-[-3px] h-[18px] w-0.5"); track.appendChild(mark);
  var note = el("p", "text-xs text-ink-400");
  box.appendChild(presets); box.appendChild(controls); box.appendChild(big); box.appendChild(track); box.appendChild(note);
  host.appendChild(box);

  var active = null;
  PRESETS.forEach(function (p) {
    var b = el("button", "btn btn-sm", p.name); b.type = "button";
    b.addEventListener("click", function () {
      A.s.value = p.a; CV.s.value = p.cv; CD.s.value = p.cd; active = p; paint();
    });
    presets.appendChild(b);
  });
  [A, CV, CD].forEach(function (c) { c.s.addEventListener("input", function () { active = null; paint(); }); });

  function pos(x) { return Math.max(0, Math.min(100, x / 2.5 * 100)); }  // scale 0..2.5x
  function paint() {
    var a = +A.s.value, cv = +CV.s.value, cd = +CD.s.value;
    A.l.textContent = "acceptance α = " + a.toFixed(2);
    CV.l.textContent = "verify cost = " + cv.toFixed(2) + " steps";
    CD.l.textContent = "draft cost = " + cd.toFixed(2) + " steps";
    var s = (1 + a) / (cv + cd);
    big.textContent = s.toFixed(2) + "× " + (s >= 1 ? "faster" : "slower");
    fill.style.width = pos(s) + "%"; fill.style.background = s >= 1 ? C.good : C.bad;
    mark.style.left = pos(1) + "%"; mark.style.background = C.text;
    note.textContent = (1 + a).toFixed(2) + " tokens per step on average, costing " + (cv + cd).toFixed(2) +
      " normal steps. The vertical line marks 1×." +
      (active ? " Measured on the M1: " + active.measured.toFixed(2) + "×; the rest of the gap is per-step overhead the model ignores." : "");
  }
  paint();
})();
