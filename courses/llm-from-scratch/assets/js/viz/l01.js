/* Lesson 1 — next-token distribution + autoregressive loop */
(function () {
  var V = LC.Viz, el = LC.el, $ = LC.$;

  var MODEL = {
    "The capital of France is": [[" Paris", 0.86], [" a", 0.04], [" the", 0.03], [" located", 0.02], [" home", 0.02], [" one", 0.01], [" known", 0.01], [" Lyon", 0.005]],
    "I went to the": [[" store", 0.14], [" park", 0.11], [" doctor", 0.09], [" beach", 0.08], [" gym", 0.07], [" airport", 0.06], [" bank", 0.05], [" library", 0.04]],
    "She opened the door and": [[" saw", 0.17], [" walked", 0.14], [" stepped", 0.11], [" looked", 0.09], [" found", 0.08], [" let", 0.05], [" closed", 0.04], [" screamed", 0.02]],
    "2 + 2 =": [[" 4", 0.93], [" 5", 0.02], [" 22", 0.01], [" four", 0.01], [" 2", 0.01], [" the", 0.005]],
    "The mitochondria is the": [[" powerhouse", 0.71], [" organelle", 0.08], [" site", 0.06], [" main", 0.04], [" cell", 0.03], [" energy", 0.02]]
  };

  var root = document.getElementById("viz-predict");
  if (root) {
    var wrap = el("div", "space-y-4");
    var picker = el("div", "flex flex-wrap gap-2");
    var promptOut = el("div", "rounded-lg border border-ink-700 bg-ink-850 px-3 py-2 font-mono text-sm text-ink-100");
    var bars = el("div", "space-y-1.5");
    var entropy = el("p", "text-xs text-ink-400");
    wrap.appendChild(picker); wrap.appendChild(promptOut); wrap.appendChild(bars); wrap.appendChild(entropy);
    root.appendChild(wrap);

    var keys = Object.keys(MODEL);
    var current = keys[0];

    function draw() {
      promptOut.innerHTML = '<span class="text-ink-400">prompt →</span> ' + current +
        '<span class="animate-pulse text-accent">▌</span>';
      bars.innerHTML = "";
      var dist = MODEL[current];
      var max = dist[0][1];
      var H = 0;
      dist.forEach(function (d) { H -= d[1] * Math.log2(d[1]); });
      dist.forEach(function (d) {
        var row = el("div", "flex items-center gap-3");
        var lab = el("code", "w-28 shrink-0 truncate rounded bg-ink-800 px-1.5 py-0.5 text-right text-xs text-ink-100",
          d[0].replace(/ /g, "␣"));
        var track = el("div", "h-5 flex-1 overflow-hidden rounded bg-ink-800");
        var fill = el("div", "h-full rounded transition-all duration-500");
        fill.style.width = (d[1] / max * 100) + "%";
        fill.style.background = V.heat(d[1] / max);
        track.appendChild(fill);
        var num = el("span", "w-14 shrink-0 text-right font-mono text-xs text-ink-400", (d[1] * 100).toFixed(1) + "%");
        row.appendChild(lab); row.appendChild(track); row.appendChild(num);
        bars.appendChild(row);
      });
      entropy.textContent = "Shown: top " + dist.length + " of a ~100,000-token vocabulary. Entropy of these ≈ " +
        H.toFixed(2) + " bits — lower means the model is more certain.";
    }

    keys.forEach(function (k) {
      var b = el("button", "btn btn-sm", k.length > 26 ? k.slice(0, 26) + "…" : k);
      b.type = "button";
      b.addEventListener("click", function () {
        current = k; draw();
        LC.$$("button", picker).forEach(function (x) { x.classList.remove("btn-primary"); });
        b.classList.add("btn-primary");
      });
      picker.appendChild(b);
      if (k === current) b.classList.add("btn-primary");
    });
    draw();
  }

  /* ---- autoregression stepper ---- */
  var ar = document.getElementById("viz-autoregress");
  if (ar) {
    var SEQ = [" The", " cat", " sat", " on", " the", " mat", " and", " fell", " asleep", "."];
    var i = 0;
    var box = el("div", "space-y-3");
    var stream = el("div", "flex min-h-[3.5rem] flex-wrap items-start gap-1.5 rounded-lg border border-ink-700 bg-ink-850 p-3");
    var info = el("p", "text-xs text-ink-400");
    var ctrls = el("div", "flex gap-2");
    var step = el("button", "btn btn-sm btn-primary", "Generate next token");
    var reset = el("button", "btn btn-sm", "Reset");
    step.type = reset.type = "button";
    ctrls.appendChild(step); ctrls.appendChild(reset);
    box.appendChild(stream); box.appendChild(info); box.appendChild(ctrls);
    ar.appendChild(box);

    function drawAR() {
      stream.innerHTML = "";
      var pr = el("span", "tok border-ink-600 bg-ink-800 text-ink-400", "[prompt]");
      stream.appendChild(pr);
      for (var k = 0; k < i; k++) {
        var t = el("span", "tok " + (k === i - 1 ? "border-accent bg-accent/20 text-ink-100" : "border-ink-700 text-ink-300"),
          SEQ[k].replace(/ /g, "␣"));
        stream.appendChild(t);
      }
      if (i < SEQ.length) {
        var q = el("span", "tok border-dashed border-ink-600 text-ink-600", "?");
        stream.appendChild(q);
      }
      info.textContent = i === 0
        ? "Step 0 — the model has only the prompt. One forward pass gives a distribution; we sample from it."
        : "Step " + i + " — forward pass #" + i + " ran over " + (i + 1) + " positions. The token just produced is now part of the input for step " + (i + 1) + ".";
      step.disabled = i >= SEQ.length;
      step.textContent = i >= SEQ.length ? "Hit end-of-text" : "Generate next token";
    }
    step.addEventListener("click", function () { if (i < SEQ.length) { i++; drawAR(); } });
    reset.addEventListener("click", function () { i = 0; drawAR(); });
    drawAR();
  }
})();
