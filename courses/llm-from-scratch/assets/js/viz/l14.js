/* Lesson 14 — preference labelling exercise */
(function () {
  var el = LC.el;
  var root = document.getElementById("viz-preference");
  if (!root) return;

  var PAIRS = [
    { q: "How do I fix a leaking tap?",
      a: "Turn off the water at the isolation valve, unscrew the tap head, replace the worn washer or O-ring, and reassemble. If it still leaks, the seat may need re-grinding.",
      b: "You should probably call a plumber. Leaking taps can be complicated and there are many possible causes.",
      better: "a", why: "Specific, actionable, correctly ordered steps, with a fallback. Helpfulness." },
    { q: "Is 17 a prime number?",
      a: "Yes! 17 is definitely prime. So is 21, since it has no factors.",
      b: "Yes. 17 has no divisors other than 1 and itself — checking 2, 3 and 4 is enough, since 5² > 17.",
      better: "b", why: "A is confidently wrong about 21 (3 × 7). Factual accuracy outweighs enthusiasm." },
    { q: "Write a haiku about debugging.",
      a: "Debugging is the process of finding and fixing errors in code. It typically involves reproducing the issue, isolating the cause, and applying a fix.",
      b: "One semicolon\nsleeps in the wrong line of code —\nthree hours of my life",
      better: "b", why: "A ignored the instruction entirely. Instruction-following." },
    { q: "My startup failed. Any thoughts?",
      a: "That's rough. Most startups fail, and it usually says more about timing and market than about you. If it helps, I'm happy to look at what happened and what you'd do differently.",
      b: "Failure is simply success in disguise! Every great entrepreneur has failed. You've got this — the next one will be the big one!",
      better: "a", why: "B is hollow cheerleading. A acknowledges reality and offers something concrete. Preference data is where tone gets shaped." }
  ];

  var i = 0, correct = 0;
  var box = el("div", "space-y-3");
  var q = el("p", "text-sm font-semibold text-ink-100");
  var opts = el("div", "grid gap-3 sm:grid-cols-2");
  var fb = el("div", "text-sm");
  var prog = el("p", "text-xs text-ink-400");
  box.appendChild(q); box.appendChild(opts); box.appendChild(fb); box.appendChild(prog);
  root.appendChild(box);

  function draw() {
    if (i >= PAIRS.length) {
      q.textContent = "Done.";
      opts.innerHTML = "";
      fb.innerHTML = "<div class='note text-sm'>You agreed with the reference labels on " + correct + " of " + PAIRS.length +
        " pairs. A reward model is trained on hundreds of thousands of judgements like these, learning to score responses the way the annotators did — including their biases. Notice how much of what you just did was about tone and format rather than facts. That is exactly what post-training installs.</div>";
      prog.textContent = "";
      return;
    }
    var p = PAIRS[i];
    q.textContent = "Prompt: " + p.q;
    opts.innerHTML = "";
    fb.innerHTML = "";
    ["a", "b"].forEach(function (k) {
      var b = el("button", "opt block whitespace-pre-line"); b.type = "button";
      b.textContent = p[k];
      b.addEventListener("click", function () {
        LC.$$("button", opts).forEach(function (n) { n.disabled = true; });
        var ok = k === p.better;
        if (ok) correct++;
        LC.$$("button", opts).forEach(function (n, idx) {
          n.dataset.state = (["a", "b"][idx] === p.better) ? "correct" : "wrong";
        });
        fb.innerHTML = "<div class='note text-sm'><strong>" + (ok ? "Matches the reference label." : "The reference label picked the other one.") +
          "</strong> " + p.why + "</div>";
        var nx = el("button", "btn btn-sm btn-primary mt-2", "Next pair"); nx.type = "button";
        nx.addEventListener("click", function () { i++; draw(); });
        fb.appendChild(nx);
      });
      opts.appendChild(b);
    });
    prog.textContent = "Pair " + (i + 1) + " of " + PAIRS.length;
  }
  draw();
})();
