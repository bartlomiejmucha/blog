/* Lesson 3 — draggable vectors + toy embedding space */
(function () {
  var C = LC.Viz.C;
  var V = LC.Viz, el = LC.el;

  var root = document.getElementById("viz-vectors");
  if (root) {
    var W = 360, H = 300, CX = W / 2, CY = H / 2, S = 60;
    var a = { x: 2, y: 1 }, b = { x: 1, y: 2 };
    var box = el("div", "flex flex-col gap-4 sm:flex-row sm:items-center");
    var svgWrap = el("div", "shrink-0");
    svgWrap.innerHTML =
      '<svg viewBox="0 0 ' + W + ' ' + H + '" class="w-full max-w-[360px] touch-none select-none">' +
      '<defs><marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">' +
      '<path d="M0,0 L8,4 L0,8 z" fill="currentColor"/></marker></defs>' +
      '<g stroke="' + C.grid + '" stroke-width="1">' +
      '<line x1="0" y1="' + CY + '" x2="' + W + '" y2="' + CY + '"/>' +
      '<line x1="' + CX + '" y1="0" x2="' + CX + '" y2="' + H + '"/></g>' +
      '<path id="arc" fill="' + C.accent + '22" stroke="none"/>' +
      '<line id="va" stroke="' + C.accent + '" stroke-width="2.5" marker-end="url(#ah)" color="' + C.accent + '"/>' +
      '<line id="vb" stroke="' + C.warm + '" stroke-width="2.5" marker-end="url(#ah)" color="' + C.warm + '"/>' +
      '<circle id="ha" r="8" fill="' + C.accent + '" opacity="0.9" style="cursor:grab"/>' +
      '<circle id="hb" r="8" fill="' + C.warm + '" opacity="0.9" style="cursor:grab"/>' +
      '<text id="la" font-size="11" fill="' + C.accent + '" font-family="monospace">a</text>' +
      '<text id="lb" font-size="11" fill="' + C.warm + '" font-family="monospace">b</text>' +
      "</svg>";
    var readout = el("div", "flex-1 space-y-2 font-mono text-sm");
    box.appendChild(svgWrap); box.appendChild(readout);
    root.appendChild(box);

    var svg = svgWrap.querySelector("svg");
    function px(v) { return { x: CX + v.x * S, y: CY - v.y * S }; }

    function draw() {
      var pa = px(a), pb = px(b);
      var set = function (id, at) { var n = svg.querySelector(id); for (var k in at) n.setAttribute(k, at[k]); };
      set("#va", { x1: CX, y1: CY, x2: pa.x, y2: pa.y });
      set("#vb", { x1: CX, y1: CY, x2: pb.x, y2: pb.y });
      set("#ha", { cx: pa.x, cy: pa.y });
      set("#hb", { cx: pb.x, cy: pb.y });
      set("#la", { x: pa.x + 10, y: pa.y - 6 });
      set("#lb", { x: pb.x + 10, y: pb.y - 6 });

      var av = [a.x, a.y], bv = [b.x, b.y];
      var dot = V.dot(av, bv), cos = V.cosine(av, bv);
      var ang = Math.acos(Math.max(-1, Math.min(1, cos))) * 180 / Math.PI;
      readout.innerHTML =
        '<div class="rounded-lg border border-ink-700 bg-ink-850 p-3 space-y-1.5">' +
        '<p class="text-accent">a = [' + V.fmt(a.x) + ", " + V.fmt(a.y) + ']</p>' +
        '<p class="text-warm">b = [' + V.fmt(b.x) + ", " + V.fmt(b.y) + ']</p>' +
        '<p class="text-ink-400">‖a‖ = ' + V.fmt(V.norm(av)) + "  ‖b‖ = " + V.fmt(V.norm(bv)) + '</p>' +
        '<p class="text-ink-100">a · b = ' + V.fmt(dot) + '</p>' +
        '<p class="text-ink-100">cos(a, b) = ' + V.fmt(cos, 3) + '</p>' +
        '<p class="text-ink-400">angle ≈ ' + ang.toFixed(1) + '°</p></div>' +
        '<p class="font-sans text-xs text-ink-400">' +
        (cos > 0.9 ? "Nearly identical direction — in embedding terms, near-synonyms."
          : cos > 0.3 ? "Related but distinct."
          : cos > -0.3 ? "Close to orthogonal — essentially unrelated."
          : "Pointing apart — opposed directions.") + '</p>';
    }

    var dragging = null;
    function point(e) {
      var r = svg.getBoundingClientRect();
      var cx = (e.touches ? e.touches[0].clientX : e.clientX) - r.left;
      var cy = (e.touches ? e.touches[0].clientY : e.clientY) - r.top;
      return { x: (cx / r.width * W - CX) / S, y: -(cy / r.height * H - CY) / S };
    }
    function start(id, vec) {
      svg.querySelector(id).addEventListener("mousedown", function () { dragging = vec; });
      svg.querySelector(id).addEventListener("touchstart", function (e) { dragging = vec; e.preventDefault(); }, { passive: false });
    }
    start("#ha", a); start("#hb", b);
    function move(e) {
      if (!dragging) return;
      var p = point(e);
      dragging.x = Math.max(-2.6, Math.min(2.6, Math.round(p.x * 10) / 10));
      dragging.y = Math.max(-2.2, Math.min(2.2, Math.round(p.y * 10) / 10));
      draw();
      if (e.preventDefault) e.preventDefault();
    }
    window.addEventListener("mousemove", move);
    window.addEventListener("touchmove", move, { passive: false });
    window.addEventListener("mouseup", function () { dragging = null; });
    window.addEventListener("touchend", function () { dragging = null; });
    draw();
  }

  /* ---------- toy embedding space ---------- */
  var sp = document.getElementById("viz-embed-space");
  if (sp) {
    var E = {
      king: [0.9, 0.8, 0.2], queen: [0.85, -0.75, 0.25], man: [0.15, 0.9, 0.1], woman: [0.1, -0.85, 0.12],
      prince: [0.7, 0.7, 0.3], princess: [0.68, -0.7, 0.32],
      Paris: [-0.7, 0.1, 0.9], France: [-0.85, 0.05, 0.75], Tokyo: [-0.65, 0.15, 0.95], Japan: [-0.8, 0.1, 0.8],
      dog: [0.2, 0.1, -0.85], cat: [0.18, -0.05, -0.9], puppy: [0.25, 0.12, -0.8],
      run: [0.4, 0.3, -0.4], running: [0.42, 0.28, -0.38], ran: [0.41, 0.32, -0.42]
    };
    var names = Object.keys(E);
    var panel = el("div", "space-y-4");
    var chips = el("div", "flex flex-wrap gap-1.5");
    var res = el("div", "rounded-lg border border-ink-700 bg-ink-850 p-3 text-sm");
    panel.appendChild(el("p", "text-xs text-ink-400", "Click a word to rank all the others by cosine similarity to it."));
    panel.appendChild(chips); panel.appendChild(res);

    var anaWrap = el("div", "space-y-2 rounded-lg border border-ink-700 bg-ink-850 p-3");
    anaWrap.appendChild(el("p", "text-xs font-semibold text-ink-100", "Analogy: a − b + c ≈ ?"));
    var sels = el("div", "flex flex-wrap items-center gap-2 font-mono text-xs");
    function sel(def) {
      var s = document.createElement("select");
      s.className = "field w-auto py-1";
      names.forEach(function (n) { var o = document.createElement("option"); o.value = o.textContent = n; s.appendChild(o); });
      s.value = def; return s;
    }
    var sA = sel("king"), sB = sel("man"), sC = sel("woman");
    var anaOut = el("span", "text-good");
    sels.appendChild(sA); sels.appendChild(el("span", "text-ink-400", "−")); sels.appendChild(sB);
    sels.appendChild(el("span", "text-ink-400", "+")); sels.appendChild(sC);
    sels.appendChild(el("span", "text-ink-400", "≈")); sels.appendChild(anaOut);
    anaWrap.appendChild(sels);
    panel.appendChild(anaWrap);
    sp.appendChild(panel);

    function neighbours(w) {
      return names.filter(function (n) { return n !== w; })
        .map(function (n) { return [n, V.cosine(E[w], E[n])]; })
        .sort(function (x, y) { return y[1] - x[1]; });
    }
    function show(w) {
      var list = neighbours(w).slice(0, 6);
      res.innerHTML = '<p class="mb-2 text-xs text-ink-400">Nearest to <span class="text-accent font-mono">' + w + "</span></p>" +
        list.map(function (p) {
          var pct = Math.round((p[1] + 1) / 2 * 100);
          return '<div class="mb-1 flex items-center gap-2"><code class="w-20 text-xs">' + p[0] + '</code>' +
            '<div class="h-2 flex-1 rounded bg-ink-800"><div class="h-full rounded" style="width:' + pct +
            '%;background:' + V.heat(p[1]) + '"></div></div>' +
            '<span class="w-12 text-right font-mono text-xs text-ink-400">' + V.fmt(p[1]) + "</span></div>";
        }).join("");
    }
    names.forEach(function (n) {
      var c = el("button", "btn btn-sm font-mono", n); c.type = "button";
      c.addEventListener("click", function () { show(n); });
      chips.appendChild(c);
    });
    show("king");

    function ana() {
      var a = E[sA.value], bb = E[sB.value], c = E[sC.value];
      var t = a.map(function (x, i) { return x - bb[i] + c[i]; });
      var best = names.filter(function (n) { return [sA.value, sB.value, sC.value].indexOf(n) === -1; })
        .map(function (n) { return [n, V.cosine(t, E[n])]; })
        .sort(function (x, y) { return y[1] - x[1]; })[0];
      anaOut.textContent = best[0] + "  (cos " + V.fmt(best[1]) + ")";
    }
    [sA, sB, sC].forEach(function (s) { s.addEventListener("change", ana); });
    ana();
  }
})();
