/* Lesson 18 — calibration: confidence vs correctness */
(function () {
  var V = LC.Viz, el = LC.el;
  var root = document.getElementById("viz-halluc");
  if (!root) return;

  var ANSWERS = [
    { q: "Capital of Australia?", a: "Canberra", p: 0.97, ok: true },
    { q: "Who wrote Pride and Prejudice?", a: "Jane Austen", p: 0.96, ok: true },
    { q: "Boiling point of water at sea level?", a: "100 °C", p: 0.95, ok: true },
    { q: "Year the Eiffel Tower opened?", a: "1889", p: 0.88, ok: true },
    { q: "Population of Reykjavik?", a: "about 140,000", p: 0.62, ok: true },
    { q: "Which paper introduced RoPE?", a: "RoFormer", p: 0.58, ok: true },
    // One confident falsehood. Without it the set separates perfectly at 0.5 and
    // the threshold looks like a free win, which is the opposite of the lesson.
    { q: "Which paper introduced layer normalisation?", a: "Attention Is All You Need", p: 0.79, ok: false },
    { q: "Middle name of the third CEO of a small firm?", a: "James", p: 0.31, ok: false },
    { q: "DOI of the 2019 paper on X?", a: "10.1145/3292500", p: 0.22, ok: false },
    { q: "Exact revenue of a private company in 2021?", a: "$412 million", p: 0.18, ok: false },
    { q: "Page number of a quote in an unnamed edition?", a: "page 217", p: 0.12, ok: false }
  ];

  var threshold = 0.5;
  var box = el("div", "space-y-3");
  var head = el("div", "flex flex-wrap items-center gap-3");
  var lab = el("span", "font-mono text-xs text-accent", "abstain below 0.50");
  var inp = document.createElement("input");
  inp.type = "range"; inp.min = 0; inp.max = 1; inp.step = 0.01; inp.value = threshold; inp.className = "slider max-w-xs";
  head.appendChild(el("span", "text-xs text-ink-400", "confidence threshold")); head.appendChild(inp); head.appendChild(lab);
  var list = el("div", "space-y-1");
  var stat = el("div", "rounded-lg border border-ink-700 bg-ink-850 p-3 text-xs space-y-1");
  box.appendChild(head); box.appendChild(list); box.appendChild(stat);
  root.appendChild(box);

  function draw() {
    threshold = parseFloat(inp.value);
    lab.textContent = "abstain below " + threshold.toFixed(2);
    list.innerHTML = "";
    var answered = 0, right = 0, wrong = 0, missed = 0, confidentWrong = false;
    ANSWERS.forEach(function (a) {
      var speak = a.p >= threshold;
      if (speak) { answered++; if (a.ok) right++; else { wrong++; if (a.p >= 0.6) confidentWrong = true; } }
      else if (a.ok) missed++;
      var row = el("div", "flex items-center gap-2 rounded border px-2 py-1 text-xs " +
        (!speak ? "border-ink-800 text-ink-600"
          : a.ok ? "border-good/40 bg-good/5 text-ink-100" : "border-bad/50 bg-bad/10 text-ink-100"));
      row.appendChild(el("span", "w-10 shrink-0 font-mono " + (speak ? "text-accent" : "text-ink-600"), a.p.toFixed(2)));
      row.appendChild(el("span", "flex-1 truncate", a.q));
      row.appendChild(el("span", "font-mono shrink-0", speak ? a.a : "— I don't know"));
      list.appendChild(row);
    });
    stat.innerHTML =
      "<p class='text-ink-400'>answered: <span class='text-ink-100'>" + answered + "</span> of " + ANSWERS.length + "</p>" +
      "<p class='text-good'>correct answers given: " + right + "</p>" +
      "<p class='text-bad'>false statements made: " + wrong + "</p>" +
      "<p class='text-warm'>correct answers withheld: " + missed + "</p>" +
      "<p class='text-ink-400 pt-1'>" +
      (confidentWrong ? "One of those false statements was made at 0.79 confidence — a fluent, well-formed falsehood that the model rated as highly as several true answers. No threshold removes it without also silencing correct answers, which is why calibration alone is not a fix."
        : wrong > 0 ? "The remaining false statements came from answers the model itself scored as low-confidence. That information was present in the logits and simply went unused."
          : missed > 0 ? "Silence is not free either: you are withholding " + missed + " correct answer(s) to buy that. Where you set this line is a product decision, not a model property."
            : "No false statements and nothing withheld — but note what it took to get here.") + "</p>";
  }
  inp.addEventListener("input", draw);
  draw();
})();
