/* Lesson 10 — temperature and truncation playground */
(function () {
  var C = LC.Viz.C;
  var V = LC.Viz, el = LC.el;
  var TOKENS = [" the", " a", " my", " his", " her", " this", " that", " one", " some", " every", " no", " any"];
  var LOGITS = [4.2, 3.6, 2.9, 2.4, 2.2, 1.9, 1.5, 1.1, 0.8, 0.4, 0.1, -0.4];

  function barList(container, probs, keepSet, opts) {
    container.innerHTML = "";
    probs.map(function (p, i) { return [TOKENS[i], p, i]; })
      .sort(function (a, b) { return b[1] - a[1]; })
      .forEach(function (d) {
        var kept = !keepSet || keepSet.indexOf(d[2]) !== -1;
        var row = el("div", "flex items-center gap-2" + (kept ? "" : " opacity-30"));
        row.appendChild(el("code", "w-16 shrink-0 text-right text-xs text-ink-300", d[0].replace(/ /g, "␣")));
        var tr = el("div", "h-4 flex-1 overflow-hidden rounded bg-ink-800");
        var fl = el("div", "h-full transition-all duration-300");
        fl.style.width = Math.max(0.5, d[1] * 100) + "%";
        fl.style.background = kept ? V.heat(Math.min(1, d[1] * 2.5)) : C.line;
        tr.appendChild(fl); row.appendChild(tr);
        row.appendChild(el("span", "w-12 text-right font-mono text-xs text-ink-400", (d[1] * 100).toFixed(1) + "%"));
        container.appendChild(row);
      });
  }

  var t = document.getElementById("viz-temperature");
  if (t) {
    var temp = 1.0;
    var box = el("div", "space-y-3");
    var head = el("div", "flex flex-wrap items-center gap-3");
    var lab = el("span", "font-mono text-sm text-accent", "T = 1.00");
    var inp = document.createElement("input");
    inp.type = "range"; inp.min = 0.05; inp.max = 2.0; inp.step = 0.05; inp.value = 1; inp.className = "slider max-w-xs";
    head.appendChild(el("span", "text-xs text-ink-400", "temperature")); head.appendChild(inp); head.appendChild(lab);
    var presets = el("div", "flex gap-2");
    [["0.1 focused", 0.1], ["0.7 default", 0.7], ["1.0 raw", 1.0], ["1.6 wild", 1.6]].forEach(function (p) {
      var b = el("button", "btn btn-sm", p[0]); b.type = "button";
      b.addEventListener("click", function () { inp.value = p[1]; upd(); });
      presets.appendChild(b);
    });
    var bars = el("div", "space-y-1.5");
    var note = el("p", "text-xs text-ink-400");
    box.appendChild(head); box.appendChild(presets); box.appendChild(bars); box.appendChild(note);
    t.appendChild(box);

    function upd() {
      temp = parseFloat(inp.value);
      lab.textContent = "T = " + temp.toFixed(2);
      var p = V.softmax(LOGITS, temp);
      barList(bars, p);
      var H = 0; p.forEach(function (v) { if (v > 0) H -= v * Math.log2(v); });
      note.textContent = "Top token: " + (p[0] * 100).toFixed(1) + "% · entropy " + H.toFixed(2) + " bits. " +
        (temp < 0.4 ? "Sharpened almost to greedy — reliable and repetitive."
          : temp > 1.3 ? "Flattened: tokens the model considers weak now get real probability, and coherence suffers."
            : "A usable range. The logits never changed — only their scaling before the softmax.");
    }
    inp.addEventListener("input", upd);
    upd();
  }

  var tr = document.getElementById("viz-truncation");
  if (tr) {
    var k = 5, p = 0.9, tTemp = 1.0;
    var outer = el("div", "space-y-3");
    // A shared temperature control: top-p's adaptivity is only visible once the
    // underlying distribution can change shape.
    var tctl = el("div", "flex flex-wrap items-center gap-3");
    var tin = document.createElement("input");
    tin.type = "range"; tin.min = 0.2; tin.max = 2.0; tin.step = 0.05; tin.value = 1; tin.className = "slider max-w-xs";
    var tlab = el("span", "font-mono text-xs text-accent", "T = 1.00");
    tctl.appendChild(el("span", "text-xs text-ink-400", "temperature of the underlying distribution"));
    tctl.appendChild(tin); tctl.appendChild(tlab);
    var box2 = el("div", "grid gap-4 sm:grid-cols-2");
    function panel(title) {
      var c = el("div", "space-y-2");
      c.appendChild(el("p", "text-sm font-semibold text-ink-100", title));
      return c;
    }
    var pk = panel("top-k"), pp = panel("top-p (nucleus)");
    var kctl = el("div", "space-y-1"), pctl = el("div", "space-y-1");
    var kin = document.createElement("input"); kin.type = "range"; kin.min = 1; kin.max = 12; kin.value = k; kin.className = "slider";
    var pin = document.createElement("input"); pin.type = "range"; pin.min = 0.1; pin.max = 1; pin.step = 0.05; pin.value = p; pin.className = "slider";
    var klab = el("p", "font-mono text-xs text-accent", "k = 5");
    var plab = el("p", "font-mono text-xs text-accent", "p = 0.90");
    kctl.appendChild(klab); kctl.appendChild(kin);
    pctl.appendChild(plab); pctl.appendChild(pin);
    var kbars = el("div", "space-y-1.5"), pbars = el("div", "space-y-1.5");
    var knote = el("p", "text-xs text-ink-400"), pnote = el("p", "text-xs text-ink-400");
    pk.appendChild(kctl); pk.appendChild(kbars); pk.appendChild(knote);
    pp.appendChild(pctl); pp.appendChild(pbars); pp.appendChild(pnote);
    box2.appendChild(pk); box2.appendChild(pp);
    outer.appendChild(tctl); outer.appendChild(box2);
    tr.appendChild(outer);

    function upd2() {
      k = +kin.value; p = +pin.value; tTemp = +tin.value;
      klab.textContent = "k = " + k; plab.textContent = "p = " + p.toFixed(2);
      tlab.textContent = "T = " + tTemp.toFixed(2);
      var probs = V.softmax(LOGITS, tTemp);
      var order = probs.map(function (v, i) { return [v, i]; }).sort(function (a, b) { return b[0] - a[0]; });
      var keepK = order.slice(0, k).map(function (o) { return o[1]; });
      var keepP = [], cum = 0;
      for (var i = 0; i < order.length; i++) { keepP.push(order[i][1]); cum += order[i][0]; if (cum >= p) break; }
      barList(kbars, probs, keepK);
      barList(pbars, probs, keepP);
      var massK = keepK.reduce(function (s, i) { return s + probs[i]; }, 0);
      knote.textContent = k + " tokens kept, covering " + (massK * 100).toFixed(1) + "% of the probability mass — a fixed count regardless of how confident the model is.";
      pnote.textContent = keepP.length + " tokens kept, covering " + (cum * 100).toFixed(1) +
        "%. Move the temperature slider: this count moves with the model's confidence, while k stays where you put it.";
    }
    kin.addEventListener("input", upd2); pin.addEventListener("input", upd2);
    tin.addEventListener("input", upd2);
    upd2();
  }
})();
