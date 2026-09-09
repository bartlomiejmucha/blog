/* Lesson 7 — sinusoidal encoding heatmap + RoPE rotation */
(function () {
  var C = LC.Viz.C;
  var V = LC.Viz, el = LC.el;

  var s = document.getElementById("viz-sinusoid");
  if (s) {
    var P = 32, D = 48;
    var g = el("div", "inline-grid gap-[1px] overflow-x-auto");
    g.style.gridTemplateColumns = "repeat(" + D + ", 0.5rem)";
    for (var pos = 0; pos < P; pos++) {
      for (var i = 0; i < D; i++) {
        var k = Math.floor(i / 2);
        var freq = 1 / Math.pow(10000, 2 * k / D);
        var v = (i % 2 === 0) ? Math.sin(pos * freq) : Math.cos(pos * freq);
        var c = el("div", "h-2");
        c.style.background = V.heat((v + 1) / 2);
        c.title = "pos " + pos + ", dim " + i + " = " + v.toFixed(3);
        g.appendChild(c);
      }
    }
    var wrap = el("div", "space-y-2");
    wrap.appendChild(g);
    wrap.appendChild(el("p", "text-xs text-ink-400",
      "Rows = positions 0–31 (top to bottom), columns = dimensions 0–47. The left columns oscillate fast and separate neighbouring positions; the right columns change slowly and separate distant regions. Together they give each position a unique fingerprint."));
    s.appendChild(wrap);
  }

  var r = document.getElementById("viz-rope");
  if (r) {
    var m = 3, nn = 7, theta = 0.35, phi = 0.6;   // phi: the content angle between q and k before any rotation
    var box = el("div", "grid gap-4 sm:grid-cols-2");
    var left = el("div", "");
    var right = el("div", "space-y-3");
    box.appendChild(left); box.appendChild(right);
    r.appendChild(box);

    left.innerHTML = '<svg viewBox="0 0 260 260" class="w-full max-w-[260px]">' +
      '<circle cx="130" cy="130" r="90" fill="none" stroke="' + C.grid + '"/>' +
      '<line x1="20" y1="130" x2="240" y2="130" stroke="' + C.grid + '"/>' +
      '<line x1="130" y1="20" x2="130" y2="240" stroke="' + C.grid + '"/>' +
      '<line id="q" stroke="' + C.accent + '" stroke-width="2.5"/>' +
      '<line id="k" stroke="' + C.warm + '" stroke-width="2.5"/>' +
      '<text id="tq" font-size="11" fill="' + C.accent + '" font-family="monospace">q (pos m)</text>' +
      '<text id="tk" font-size="11" fill="' + C.warm + '" font-family="monospace">k (pos n)</text></svg>';
    var svg = left.querySelector("svg");

    function sl(label, min, max, val, cb) {
      var w = el("div", "space-y-1");
      var t = el("div", "flex justify-between text-xs");
      t.appendChild(el("span", "text-ink-400", label));
      var o = el("span", "font-mono text-accent", String(val));
      t.appendChild(o);
      var inp = document.createElement("input");
      inp.type = "range"; inp.min = min; inp.max = max; inp.step = 1; inp.value = val; inp.className = "slider";
      inp.addEventListener("input", function () { o.textContent = inp.value; cb(parseInt(inp.value, 10)); });
      w.appendChild(t); w.appendChild(inp);
      return w;
    }
    var readout = el("div", "rounded-lg border border-ink-700 bg-ink-850 p-3 font-mono text-xs space-y-1");
    right.appendChild(sl("position m (query)", 0, 20, m, function (v) { m = v; draw(); }));
    right.appendChild(sl("position n (key)", 0, 20, nn, function (v) { nn = v; draw(); }));
    right.appendChild(sl("content angle φ (×0.1 rad)", 0, 31, Math.round(phi * 10), function (v) { phi = v / 10; draw(); }));
    right.appendChild(readout);
    right.appendChild(el("p", "text-xs text-ink-400",
      "Move both position sliders while keeping the gap the same — the dot product does not change. That is the whole point of RoPE: the score depends on m − n, not on m and n separately. The third slider is what q and k already had to say about each other before any rotation; RoPE shifts that score by the distance, it does not replace it."));
    right.appendChild(el("p", "text-xs text-ink-400",
      "One pair at one frequency oscillates as the gap grows rather than fading. The decay-with-distance that RoPE is known for appears only once all the pairs, rotating at geometrically spaced rates, are summed together."));

    function draw() {
      // q starts at the content angle phi and is rotated by m*theta; k starts at 0
      // and is rotated by n*theta. The angle drawn between them is what cos() below reads.
      var aq = phi + m * theta, ak = nn * theta;
      function set(id, ang, R) {
        var n = svg.querySelector(id);
        n.setAttribute("x1", 130); n.setAttribute("y1", 130);
        n.setAttribute("x2", 130 + Math.cos(ang) * R); n.setAttribute("y2", 130 - Math.sin(ang) * R);
      }
      set("#q", aq, 90); set("#k", ak, 78);
      svg.querySelector("#tq").setAttribute("x", 130 + Math.cos(aq) * 100 - 20);
      svg.querySelector("#tq").setAttribute("y", 130 - Math.sin(aq) * 100);
      svg.querySelector("#tk").setAttribute("x", 130 + Math.cos(ak) * 88 - 20);
      svg.querySelector("#tk").setAttribute("y", 130 - Math.sin(ak) * 88);
      var dot = Math.cos(aq - ak);
      readout.innerHTML =
        "<p class='text-ink-400'>rotation angle = position × θ&nbsp;&nbsp;(θ = " + theta + ")</p>" +
        "<p class='text-accent'>q rotated by " + (m * theta).toFixed(2) + " rad</p>" +
        "<p class='text-warm'>k rotated by " + (nn * theta).toFixed(2) + " rad</p>" +
        "<p class='text-ink-400'>relative distance m − n = " + (m - nn) + "</p>" +
        "<p class='text-ink-400'>content angle φ = " + phi.toFixed(1) + " rad</p>" +
        "<p class='text-ink-100'>q · k ∝ cos(φ + (m − n)θ) = " + dot.toFixed(3) + "</p>";
    }
    draw();
  }
})();
