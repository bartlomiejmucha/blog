/* Lesson 12 — loss curve + gradient descent */
(function () {
  var C = LC.Viz.C;
  var V = LC.Viz, el = LC.el;

  var l = document.getElementById("viz-loss");
  if (l) {
    var p = 0.5;
    var box = el("div", "grid gap-4 sm:grid-cols-2");
    var left = el("div", "space-y-2"), right = el("div", "space-y-2");
    box.appendChild(left); box.appendChild(right);
    l.appendChild(box);

    var W = 300, H = 200;
    left.innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" class="w-full"><g id="g"></g></svg>';
    var g = left.querySelector("#g");

    var inp = document.createElement("input");
    inp.type = "range"; inp.min = 0.01; inp.max = 1; inp.step = 0.01; inp.value = p; inp.className = "slider";
    var readout = el("div", "rounded-lg border border-ink-700 bg-ink-850 p-3 font-mono text-xs space-y-1");
    right.appendChild(el("p", "text-xs text-ink-400", "probability the model assigned to the correct next token"));
    right.appendChild(inp);
    right.appendChild(readout);
    var note = el("p", "text-xs text-ink-400");
    right.appendChild(note);

    function draw() {
      var pts = [];
      for (var x = 0.01; x <= 1; x += 0.01) {
        pts.push((20 + x * (W - 30)) + "," + (H - 15 - Math.min(-Math.log(x), 4.6) / 4.6 * (H - 30)));
      }
      var cx = 20 + p * (W - 30), cy = H - 15 - Math.min(-Math.log(p), 4.6) / 4.6 * (H - 30);
      g.innerHTML =
        '<line x1="20" y1="' + (H - 15) + '" x2="' + (W - 8) + '" y2="' + (H - 15) + '" stroke="' + C.grid + '"/>' +
        '<line x1="20" y1="8" x2="20" y2="' + (H - 15) + '" stroke="' + C.grid + '"/>' +
        '<polyline points="' + pts.join(" ") + '" fill="none" stroke="' + C.accent + '" stroke-width="2"/>' +
        '<circle cx="' + cx + '" cy="' + cy + '" r="5" fill="' + C.warm + '"/>' +
        '<text x="24" y="18" font-size="10" fill="' + C.muted + '" font-family="monospace">loss</text>' +
        '<text x="' + (W - 60) + '" y="' + (H - 3) + '" font-size="10" fill="' + C.muted + '" font-family="monospace">P(correct)</text>';
      var loss = -Math.log(p);
      readout.innerHTML =
        "<p class='text-ink-400'>P(correct token) = <span class='text-accent'>" + p.toFixed(2) + "</span></p>" +
        "<p class='text-ink-100'>loss = −log(" + p.toFixed(2) + ") = " + loss.toFixed(3) + "</p>" +
        "<p class='text-ink-400'>perplexity = e^loss = " + Math.exp(loss).toFixed(2) + "</p>";
      note.textContent = p > 0.8 ? "Confident and right: almost no gradient signal, nothing much to learn here."
        : p > 0.3 ? "Typical territory for a well-trained model on ordinary text."
          : "Confidently wrong. The loss climbs steeply as the assigned probability approaches zero — this is where the largest updates come from.";
    }
    inp.addEventListener("input", function () { p = parseFloat(inp.value); draw(); });
    draw();
  }

  var d = document.getElementById("viz-descent");
  if (d) {
    var lr = 0.1, pos = -2.4, path = [pos];
    var DW = 420, DH = 220;
    function loss(x) { return 0.35 * x * x + 0.4 * Math.sin(3 * x) + 1; }
    function grad(x) { return 0.7 * x + 1.2 * Math.cos(3 * x); }

    var box2 = el("div", "space-y-3");
    var svgw = el("div", "");
    var ctr = el("div", "flex flex-wrap items-center gap-3");
    var lrl = el("span", "font-mono text-xs text-accent", "lr = 0.10");
    var lrin = document.createElement("input");
    // Max 3.0: the quadratic term has curvature 0.7, so steps only actually
    // diverge past roughly 2/0.7, and the figure promises to show divergence.
    lrin.type = "range"; lrin.min = 0.01; lrin.max = 3; lrin.step = 0.01; lrin.value = lr; lrin.className = "slider max-w-[10rem]";
    var stepB = el("button", "btn btn-sm btn-primary", "Step"); stepB.type = "button";
    var run = el("button", "btn btn-sm", "Run 20"); run.type = "button";
    var rst = el("button", "btn btn-sm", "Reset"); rst.type = "button";
    ctr.appendChild(el("span", "text-xs text-ink-400", "learning rate")); ctr.appendChild(lrin); ctr.appendChild(lrl);
    ctr.appendChild(stepB); ctr.appendChild(run); ctr.appendChild(rst);
    var note2 = el("p", "text-xs text-ink-400");
    box2.appendChild(svgw); box2.appendChild(ctr); box2.appendChild(note2);
    d.appendChild(box2);

    function X(x) { return DW / 2 + x * 70; }
    function Y(y) { return DH - 20 - y * 40; }
    function draw2() {
      var curve = [];
      for (var x = -3; x <= 3; x += 0.05) curve.push(X(x) + "," + Y(loss(x)));
      var dots = path.map(function (x, i) {
        return '<circle cx="' + X(x) + '" cy="' + Y(loss(x)) + '" r="' + (i === path.length - 1 ? 5 : 2.5) +
          '" fill="' + (i === path.length - 1 ? C.warm : C.accent) + '" opacity="' + (i === path.length - 1 ? 1 : 0.5) + '"/>';
      }).join("");
      svgw.innerHTML = '<svg viewBox="0 0 ' + DW + " " + DH + '" class="w-full">' +
        '<polyline points="' + curve.join(" ") + '" fill="none" stroke="' + C.line + '" stroke-width="2"/>' + dots +
        '<text x="8" y="16" font-size="10" fill="' + C.muted + '" font-family="monospace">loss</text>' +
        '<text x="' + (DW - 70) + '" y="' + (DH - 4) + '" font-size="10" fill="' + C.muted + '" font-family="monospace">weight value</text></svg>';
      note2.textContent = "step " + (path.length - 1) + " · weight = " + pos.toFixed(3) +
        " · loss = " + loss(pos).toFixed(3) + " · gradient = " + grad(pos).toFixed(3) + ". " +
        (lr > 2.2 ? "Diverging: each step is larger than the curvature can absorb, so it overshoots further than the last and the weight slams between the extremes. No amount of training fixes this."
          : lr > 0.55 ? "Too large: the path oscillates around the minimum instead of settling into it."
            : lr < 0.05 ? "Very small steps. Stable, but slow — and watch where it stops: it settles in the first dip it meets rather than the deepest one."
              : "A workable rate. Note it can still settle in a local dip rather than the global minimum.");
    }
    function stepOnce() {
      pos = Math.max(-3, Math.min(3, pos - lr * grad(pos)));
      path.push(pos);
      if (path.length > 60) path.shift();
      draw2();
    }
    lrin.addEventListener("input", function () { lr = parseFloat(lrin.value); lrl.textContent = "lr = " + lr.toFixed(2); draw2(); });
    stepB.addEventListener("click", stepOnce);
    run.addEventListener("click", function () { for (var i = 0; i < 20; i++) stepOnce(); });
    rst.addEventListener("click", function () { pos = -2.4; path = [pos]; draw2(); });
    draw2();
  }
})();
