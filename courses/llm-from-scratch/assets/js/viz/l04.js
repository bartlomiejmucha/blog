/* Lesson 4 — neuron, matmul, activations */
(function () {
  var C = LC.Viz.C;
  var V = LC.Viz, el = LC.el;

  function slider(label, min, max, step, val, onChange) {
    var row = el("div", "space-y-1");
    var top = el("div", "flex items-center justify-between text-xs");
    top.appendChild(el("span", "text-ink-400", label));
    var out = el("span", "font-mono text-accent", String(val));
    top.appendChild(out);
    var inp = document.createElement("input");
    inp.type = "range"; inp.min = min; inp.max = max; inp.step = step; inp.value = val;
    inp.className = "slider";
    inp.addEventListener("input", function () { out.textContent = inp.value; onChange(parseFloat(inp.value)); });
    row.appendChild(top); row.appendChild(inp);
    return row;
  }

  /* ---- single neuron ---- */
  var root = document.getElementById("viz-neuron");
  if (root) {
    var w = [0.5, -1.0, 2.0], x = [2, 1, 0.5], bias = 1.0, act = "relu";
    var box = el("div", "grid gap-4 sm:grid-cols-2");
    var ctrl = el("div", "space-y-3");
    var out = el("div", "space-y-2");
    box.appendChild(ctrl); box.appendChild(out);
    root.appendChild(box);

    for (var i = 0; i < 3; i++) (function (i) {
      ctrl.appendChild(slider("input x" + (i + 1), -3, 3, 0.1, x[i], function (v) { x[i] = v; draw(); }));
      ctrl.appendChild(slider("weight w" + (i + 1), -3, 3, 0.1, w[i], function (v) { w[i] = v; draw(); }));
    })(i);
    ctrl.appendChild(slider("bias b", -3, 3, 0.1, bias, function (v) { bias = v; draw(); }));
    var pick = el("div", "flex gap-2 pt-1");
    ["relu", "gelu", "tanh", "none"].forEach(function (a) {
      var b = el("button", "btn btn-sm" + (a === act ? " btn-primary" : ""), a); b.type = "button";
      b.addEventListener("click", function () {
        act = a;
        LC.$$("button", pick).forEach(function (n) { n.classList.remove("btn-primary"); });
        b.classList.add("btn-primary"); draw();
      });
      pick.appendChild(b);
    });
    ctrl.appendChild(pick);

    function apply(z) {
      if (act === "relu") return Math.max(0, z);
      if (act === "tanh") return Math.tanh(z);
      if (act === "gelu") return 0.5 * z * (1 + Math.tanh(Math.sqrt(2 / Math.PI) * (z + 0.044715 * z * z * z)));
      return z;
    }

    function draw() {
      var terms = w.map(function (wi, i) { return wi * x[i]; });
      var z = terms.reduce(function (a, b) { return a + b; }, 0) + bias;
      var y = apply(z);
      out.innerHTML =
        '<div class="rounded-lg border border-ink-700 bg-ink-850 p-3 font-mono text-xs space-y-1.5">' +
        terms.map(function (t, i) {
          return '<p class="text-ink-400">w' + (i + 1) + "·x" + (i + 1) + " = " + V.fmt(w[i]) + " × " + V.fmt(x[i]) +
            ' = <span class="text-ink-100">' + V.fmt(t) + "</span></p>";
        }).join("") +
        '<p class="text-ink-400">+ bias = ' + V.fmt(bias) + "</p>" +
        '<hr class="border-ink-700">' +
        '<p class="text-ink-100">z = ' + V.fmt(z) + "</p>" +
        '<p class="text-good">y = ' + act + "(z) = " + V.fmt(y) + "</p></div>" +
        '<div class="h-3 rounded bg-ink-800"><div class="h-full rounded transition-all" style="width:' +
        Math.min(100, Math.abs(y) / 6 * 100) + "%;background:" + (y >= 0 ? C.good : C.bad) + '"></div></div>' +
        '<p class="text-xs text-ink-400">' + (act === "relu" && z < 0
          ? "z is negative and ReLU clamps it to zero. This neuron is silent — and its gradient here is zero, which is how ReLU neurons die."
          : "The weighted sum is a dot product: the neuron measures how much the input points along its weight vector.") + "</p>";
    }
    draw();
  }

  /* ---- matmul ---- */
  var mm = document.getElementById("viz-matmul");
  if (mm) {
    var A = [[1, 2, 0], [0, 1, 3]];          // 2x3
    var B = [[2, 1], [0, 3], [1, 0]];        // 3x2
    var box2 = el("div", "space-y-3");
    var grid = el("div", "flex flex-wrap items-center gap-4");
    var note = el("p", "text-xs text-ink-400", "Hover any output cell to see the row and column that produced it.");
    box2.appendChild(grid); box2.appendChild(note);
    mm.appendChild(box2);

    function matNode(M, label, cls) {
      var wrap = el("div", "space-y-1");
      wrap.appendChild(el("p", "text-center font-mono text-xs text-ink-400", label));
      var g = el("div", "inline-grid gap-1");
      g.style.gridTemplateColumns = "repeat(" + M[0].length + ", minmax(0, 2.2rem))";
      M.forEach(function (row, r) {
        row.forEach(function (v, c) {
          var cell = el("div", "flex h-9 items-center justify-center rounded border border-ink-700 bg-ink-850 font-mono text-xs text-ink-100", String(v));
          cell.dataset.r = r; cell.dataset.c = c; cell.dataset.m = cls;
          g.appendChild(cell);
        });
      });
      wrap.appendChild(g);
      return wrap;
    }

    // Named P, not C: C is the shared palette declared at the top of this file.
    var P = A.map(function (row) {
      return B[0].map(function (_, c) {
        return row.reduce(function (s, v, k) { return s + v * B[k][c]; }, 0);
      });
    });

    grid.appendChild(matNode(A, "A  [2×3]", "a"));
    grid.appendChild(el("span", "font-mono text-ink-400 text-lg", "×"));
    grid.appendChild(matNode(B, "B  [3×2]", "b"));
    grid.appendChild(el("span", "font-mono text-ink-400 text-lg", "="));
    grid.appendChild(matNode(P, "C  [2×2]", "c"));

    LC.$$('[data-m="c"]', mm).forEach(function (cell) {
      cell.addEventListener("mouseenter", function () {
        var r = +cell.dataset.r, c = +cell.dataset.c;
        LC.$$('[data-m="a"]', mm).forEach(function (n) { n.classList.toggle("border-accent", +n.dataset.r === r); });
        LC.$$('[data-m="b"]', mm).forEach(function (n) { n.classList.toggle("border-warm", +n.dataset.c === c); });
        cell.classList.add("border-good");
        var terms = A[r].map(function (v, k) { return v + "×" + B[k][c]; }).join(" + ");
        note.innerHTML = 'C[' + r + "][" + c + "] = " + terms + " = <span class='text-good font-mono'>" + P[r][c] +
          "</span> — the dot product of row " + r + " of A with column " + c + " of B.";
      });
      cell.addEventListener("mouseleave", function () {
        LC.$$("[data-m]", mm).forEach(function (n) { n.classList.remove("border-accent", "border-warm", "border-good"); });
        note.textContent = "Hover any output cell to see the row and column that produced it.";
      });
    });
  }

  /* ---- activation plots ---- */
  var ac = document.getElementById("viz-activations");
  if (ac) {
    var fns = {
      ReLU: function (x) { return Math.max(0, x); },
      GELU: function (x) { return 0.5 * x * (1 + Math.tanh(Math.sqrt(2 / Math.PI) * (x + 0.044715 * x * x * x))); },
      SiLU: function (x) { return x / (1 + Math.exp(-x)); },
      tanh: Math.tanh
    };
    var W = 300, H = 200, cx = W / 2, cy = H / 2, sc = 30;
    var wrap = el("div", "flex flex-wrap gap-4");
    Object.keys(fns).forEach(function (name) {
      var f = fns[name];
      var pts = [];
      for (var x = -4; x <= 4; x += 0.05) pts.push((cx + x * sc) + "," + (cy - f(x) * sc));
      var card = el("div", "figure flex-1 min-w-[220px]");
      card.innerHTML = '<p class="figure-title">' + name + "</p>" +
        '<svg viewBox="0 0 ' + W + " " + H + '" class="w-full">' +
        '<line x1="0" y1="' + cy + '" x2="' + W + '" y2="' + cy + '" stroke="' + C.grid + '"/>' +
        '<line x1="' + cx + '" y1="0" x2="' + cx + '" y2="' + H + '" stroke="' + C.grid + '"/>' +
        '<polyline points="' + pts.join(" ") + '" fill="none" stroke="' + C.accent + '" stroke-width="2"/></svg>' +
        '<p class="mt-1 text-xs text-ink-400">' +
        ({ ReLU: "Hard zero below 0. Cheap, but dead neurons get no gradient.",
           GELU: "Smooth, lets small negatives through. GPT default.",
           SiLU: "x·sigmoid(x). The building block of SwiGLU.",
           tanh: "Saturates at ±1 — gradients vanish at the extremes." })[name] + "</p>";
      wrap.appendChild(card);
    });
    ac.appendChild(wrap);
  }
})();
