/* Lesson 9 — forward pass stepper + depth sharpening */
(function () {
  var V = LC.Viz, el = LC.el;

  var f = document.getElementById("viz-forward");
  if (f) {
    var STAGES = [
      { n: "raw text", s: '"The capital of France"', d: "4 words of a string." },
      { n: "token ids", s: "[791, 6864, 315, 9822]", d: "Shape [4]. The tokenizer's output — the model sees only these integers." },
      { n: "embeddings", s: "[4, 4096]", d: "Each id becomes a 4096-dimensional vector by table lookup." },
      { n: "after block 1", s: "[4, 4096]", d: "Attention has mixed information between positions; the FFN has transformed each one." },
      { n: "after block 16", s: "[4, 4096]", d: "Mid-stack: syntax resolved, entities tracked, facts being retrieved." },
      { n: "after block 32", s: "[4, 4096]", d: "Late layers have shifted from 'what is being said' toward 'what token comes next'." },
      { n: "final norm", s: "[4, 4096]", d: "One last normalisation before the output projection." },
      { n: "logits", s: "[4, 128000]", d: "One unnormalised score per vocabulary entry, at every position." },
      { n: "softmax(last row)", s: "[128000] → ' Paris' 0.86", d: "Only the last position matters for generating the next token. The rest are discarded." }
    ];
    var i = 0;
    var box = el("div", "space-y-3");
    var track = el("div", "flex flex-wrap gap-1");
    var panel = el("div", "rounded-lg border border-ink-700 bg-ink-850 p-3 space-y-1");
    var ctr = el("div", "flex gap-2");
    var prev = el("button", "btn btn-sm", "←");
    var next = el("button", "btn btn-sm btn-primary", "Next stage →");
    prev.type = next.type = "button";
    ctr.appendChild(prev); ctr.appendChild(next);
    box.appendChild(track); box.appendChild(panel); box.appendChild(ctr);
    f.appendChild(box);

    function draw() {
      track.innerHTML = "";
      STAGES.forEach(function (s, k) {
        var c = el("span", "rounded px-2 py-1 font-mono text-[10px] " +
          (k === i ? "bg-accent/25 text-ink-100 border border-accent" : k < i ? "bg-ink-800 text-ink-400" : "bg-ink-900 text-ink-600"), s.n);
        track.appendChild(c);
      });
      panel.innerHTML = '<p class="font-mono text-sm text-accent">' + STAGES[i].s + "</p>" +
        '<p class="text-xs text-ink-400">' + STAGES[i].d + "</p>";
      prev.disabled = i === 0; next.disabled = i === STAGES.length - 1;
    }
    prev.addEventListener("click", function () { if (i > 0) { i--; draw(); } });
    next.addEventListener("click", function () { if (i < STAGES.length - 1) { i++; draw(); } });
    draw();
  }

  var ly = document.getElementById("viz-layers");
  if (ly) {
    var toks = [" Paris", " France", " the", " a", " Lyon", " city"];
    var base = [3.0, 1.4, 1.2, 1.0, 0.9, 0.8];
    var layer = 32;
    var box2 = el("div", "space-y-3");
    var slwrap = el("div", "space-y-1");
    var t = el("div", "flex justify-between text-xs");
    t.appendChild(el("span", "text-ink-400", "read out from layer"));
    var lo = el("span", "font-mono text-accent", "32");
    t.appendChild(lo);
    var inp = document.createElement("input");
    inp.type = "range"; inp.min = 1; inp.max = 32; inp.value = 32; inp.className = "slider";
    slwrap.appendChild(t); slwrap.appendChild(inp);
    var bars = el("div", "space-y-1.5");
    var note = el("p", "text-xs text-ink-400");
    box2.appendChild(slwrap); box2.appendChild(bars); box2.appendChild(note);
    ly.appendChild(box2);

    function draw2() {
      var sharp = Math.pow(layer / 32, 2.2);
      var p = V.softmax(base.map(function (b) { return b * sharp; }));
      bars.innerHTML = "";
      p.map(function (v, i) { return [toks[i], v]; })
        .sort(function (a, b) { return b[1] - a[1]; })
        .forEach(function (d) {
          var row = el("div", "flex items-center gap-2");
          row.appendChild(el("code", "w-20 shrink-0 text-right text-xs text-ink-300", d[0].replace(/ /g, "␣")));
          var tr = el("div", "h-4 flex-1 overflow-hidden rounded bg-ink-800");
          var fl = el("div", "h-full transition-all duration-300");
          fl.style.width = (d[1] * 100) + "%"; fl.style.background = V.heat(d[1]);
          tr.appendChild(fl);
          row.appendChild(tr);
          row.appendChild(el("span", "w-12 text-right font-mono text-xs text-ink-400", (d[1] * 100).toFixed(0) + "%"));
          bars.appendChild(row);
        });
      note.textContent = layer < 10
        ? "Early layers: the distribution is nearly flat. The model has not yet committed to an answer."
        : layer < 24
          ? "Middle layers: the correct answer is emerging as facts are retrieved and combined."
          : "Late layers: probability has concentrated sharply on the final prediction.";
    }
    inp.addEventListener("input", function () { layer = +inp.value; lo.textContent = inp.value; draw2(); });
    draw2();
  }
})();
