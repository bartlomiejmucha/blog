/* Lesson 8 — block dataflow + pre/post norm stability */
(function () {
  var C = LC.Viz.C;
  var V = LC.Viz, el = LC.el;

  var b = document.getElementById("viz-block");
  if (b) {
    var residual = true, step = 0;
    var box = el("div", "space-y-3");
    var flow = el("div", "space-y-2");
    var ctrls = el("div", "flex flex-wrap gap-2");
    var next = el("button", "btn btn-sm btn-primary", "Next step");
    var reset = el("button", "btn btn-sm", "Reset");
    var toggle = el("button", "btn btn-sm", "Residuals: on");
    [next, reset, toggle].forEach(function (x) { x.type = "button"; ctrls.appendChild(x); });
    var msg = el("p", "text-xs text-ink-400");
    box.appendChild(flow); box.appendChild(ctrls); box.appendChild(msg);
    b.appendChild(box);

    var STEPS = [
      ["x enters the block", "The residual stream at this position — a vector of d_model numbers carrying everything accumulated so far."],
      ["Norm(x)", "A normalised copy is made. The original x is untouched and continues down the residual path."],
      ["Attention(Norm(x))", "This sub-layer reads the other positions and produces an update."],
      ["x = x + Attention(...)", "The update is added back. Nothing was overwritten."],
      ["Norm(x)", "Normalise again for the second sub-layer."],
      ["FFN(Norm(x))", "Position-wise expand → activate → contract. No sideways communication here."],
      ["x = x + FFN(...)", "Added back. The block is done and the shape is unchanged: [T, d] in, [T, d] out."]
    ];

    function draw() {
      flow.innerHTML = "";
      STEPS.forEach(function (s, i) {
        var active = i === step, past = i < step;
        var row = el("div", "rounded-xl border px-3 py-2 transition " +
          (active ? "border-accent bg-accent/10" : past ? "border-ink-700 bg-ink-850/60" : "border-ink-800 bg-ink-900/40 opacity-40"));
        row.appendChild(el("p", "font-mono text-sm " + (active ? "text-ink-100" : "text-ink-400"), s[0]));
        if (active) row.appendChild(el("p", "mt-1 text-xs text-ink-400",
          (!residual && (i === 3 || i === 6))
            ? "Residuals are OFF: the sub-layer output REPLACES x. In a real 96-layer stack this destroys the gradient path and the model will not train."
            : s[1]));
        flow.appendChild(row);
      });
      msg.textContent = "Step " + (step + 1) + " of " + STEPS.length + ".";
      next.textContent = step >= STEPS.length - 1 ? "Start over" : "Next step";
    }
    next.addEventListener("click", function () { step = step >= STEPS.length - 1 ? 0 : step + 1; draw(); });
    reset.addEventListener("click", function () { step = 0; draw(); });
    toggle.addEventListener("click", function () {
      residual = !residual;
      toggle.textContent = "Residuals: " + (residual ? "on" : "off");
      toggle.classList.toggle("btn-primary", !residual);
      draw();
    });
    draw();
  }

  var nm = document.getElementById("viz-norm");
  if (nm) {
    var W = 520, H = 190;
    function series(pre) {
      var pts = [], mag = 1;
      for (var l = 0; l <= 48; l++) {
        pts.push([l, mag]);
        // Pre-norm: steady additive growth down an untouched residual path.
        // Post-norm: multiplicative, so the swings compound with depth.
        mag = pre ? mag + 0.12 + Math.sin(l) * 0.02
                  : mag * (1 + 0.085 + Math.sin(l * 1.7) * 0.42);
        mag = Math.max(0.05, Math.min(mag, 14));
      }
      return pts;
    }
    function path(pts, color) {
      return '<polyline fill="none" stroke="' + color + '" stroke-width="2" points="' +
        pts.map(function (p) { return (20 + p[0] / 48 * (W - 40)) + "," + (H - 20 - Math.min(p[1], 12) / 12 * (H - 40)); }).join(" ") + '"/>';
    }
    var wrap = el("div", "space-y-2");
    wrap.innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" class="w-full">' +
      '<line x1="20" y1="' + (H - 20) + '" x2="' + (W - 20) + '" y2="' + (H - 20) + '" stroke="' + C.grid + '"/>' +
      '<line x1="20" y1="10" x2="20" y2="' + (H - 20) + '" stroke="' + C.grid + '"/>' +
      path(series(true), C.good) + path(series(false), C.bad) +
      '<text x="30" y="24" font-size="11" fill="' + C.good + '" font-family="monospace">pre-norm: smooth, controlled growth</text>' +
      '<text x="30" y="40" font-size="11" fill="' + C.bad + '" font-family="monospace">post-norm: erratic, prone to divergence</text>' +
      "</svg>";
    wrap.appendChild(el("p", "text-xs text-ink-400",
      "Illustrative activation magnitude versus layer depth. Pre-norm keeps a clean additive residual path so magnitude grows predictably; post-norm normalises the path itself, and deep stacks become unstable without careful warmup."));
    nm.appendChild(wrap);
  }
})();
