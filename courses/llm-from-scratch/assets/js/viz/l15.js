/* Lesson 15 — ICL attention, CoT compute, prompt lab */
(function () {
  var C = LC.Viz.C;
  var V = LC.Viz, el = LC.el;

  var icl = document.getElementById("viz-icl");
  if (icl) {
    var EX = [["dog", "chien"], ["house", "maison"], ["water", "eau"]];
    var shown = 1;
    var box = el("div", "space-y-3");
    var ctr = el("div", "flex gap-2");
    var pane = el("div", "rounded-lg border border-ink-700 bg-ink-850 p-3 font-mono text-xs leading-6");
    var note = el("p", "text-xs text-ink-400");
    box.appendChild(ctr); box.appendChild(pane); box.appendChild(note);
    icl.appendChild(box);

    [0, 1, 2, 3].forEach(function (n) {
      var b = el("button", "btn btn-sm" + (n === shown ? " btn-primary" : ""), n + "-shot"); b.type = "button";
      b.addEventListener("click", function () {
        shown = n;
        LC.$$("button", ctr).forEach(function (x) { x.classList.remove("btn-primary"); });
        b.classList.add("btn-primary"); draw();
      });
      ctr.appendChild(b);
    });

    function draw() {
      var lines = EX.slice(0, shown).map(function (e) {
        return '<span class="text-ink-400">English:</span> ' + e[0] + '  <span class="text-ink-400">French:</span> <span class="text-accent">' + e[1] + "</span>";
      });
      lines.push('<span class="text-ink-400">English:</span> book  <span class="text-ink-400">French:</span> <span class="text-good">' +
        (shown === 0 ? "?" : "livre") + "</span>" + (shown > 0 ? ' <span class="text-ink-600">← copying the established pattern</span>' : ""));
      pane.innerHTML = lines.join("<br>");
      note.textContent = shown === 0
        ? "With no examples the model must infer the task from the field names alone. It often works, and it is much less reliable about format."
        : "With " + shown + " example(s), induction-style circuits attend back to the earlier 'French:' positions and continue the same structure. No weight changed — this is all forward-pass pattern completion. Notice that the format, not the vocabulary, is what is being copied.";
    }
    draw();
  }

  var cot = document.getElementById("viz-cot");
  if (cot) {
    var box2 = el("div", "grid gap-4 sm:grid-cols-2");
    function panel(title, tokens, text, colour) {
      var c = el("div", "figure");
      c.appendChild(el("p", "figure-title", title));
      var body = el("pre", "whitespace-pre-wrap rounded bg-ink-850 p-2 font-mono text-[11px] leading-5 text-ink-300");
      body.textContent = text;
      c.appendChild(body);
      var row = el("div", "mt-2 flex flex-wrap gap-[3px]");
      for (var i = 0; i < tokens; i++) {
        var d = el("div", "h-2.5 w-2.5 rounded-[2px]");
        d.style.background = colour;
        row.appendChild(d);
      }
      c.appendChild(row);
      c.appendChild(el("p", "mt-1 text-xs text-ink-400", tokens + " generated tokens = " + tokens + " full forward passes of compute applied to this problem."));
      return c;
    }
    box2.appendChild(panel("Direct answer", 2,
      "Q: A shop has 23 apples, sells 7,\n   then buys 12 more. How many?\nA: 28", C.bad));
    box2.appendChild(panel("Chain of thought", 34,
      "Q: A shop has 23 apples, sells 7,\n   then buys 12 more. How many?\nA: Start with 23.\n   Sells 7: 23 - 7 = 16.\n   Buys 12: 16 + 12 = 28.\n   The answer is 28.", C.good));
    cot.appendChild(box2);
    var n = el("p", "mt-3 text-xs text-ink-400");
    n.textContent = "Both reach 28. The right-hand version applied roughly 17× more sequential computation to get there, and each intermediate result sits in the context where the final step can attend to it directly. On harder problems that difference decides whether the answer is right.";
    cot.appendChild(n);
  }

  var pl = document.getElementById("viz-prompt");
  if (pl) {
    var CHECKS = [
      { id: "format", label: "Specifies the exact output format", test: /json|list|bullet|format|schema|table|one word|integer|yes or no|array/i },
      { id: "delim", label: "Uses delimiters or clear sections", test: /```|---|<<<|<[a-z_]+>|"""|###/ },
      { id: "cot", label: "Asks for reasoning before the answer", test: /step by step|reason|think|explain .*(then|before)|working/i },
      { id: "escape", label: "Gives an escape hatch for missing information", test: /unknown|not (stated|say|present|mentioned)|don't know|do not know|insufficient|n\/a/i },
      { id: "role", label: "Sets a role or context", test: /you are|act as|as an? (expert|senior|experienced)/i },
      { id: "example", label: "Includes at least one worked example", test: /example|e\.g\.|input:|output:/i }
    ];
    var box3 = el("div", "space-y-3");
    var ta = document.createElement("textarea");
    ta.className = "field h-36 leading-6";
    ta.value = "Extract the people mentioned in the text below.\n\nText: <<<{{document}}>>>";
    var res = el("div", "space-y-1.5");
    var score = el("p", "text-sm font-semibold");
    var samples = el("div", "flex flex-wrap gap-2");
    [["weak prompt", "Extract the people mentioned in the text below.\n\nText: <<<{{document}}>>>"],
     ["strong prompt", "You are a careful information extractor.\n\nRead the document between the delimiters and list every person named in it.\n\nReturn a JSON array of objects with keys \"name\" and \"role\". If the document names no people, return an empty array. If a role is not stated, use \"unknown\".\n\nExample:\nInput: \"Dr Reed chaired the meeting.\"\nOutput: [{\"name\": \"Dr Reed\", \"role\": \"chair\"}]\n\nDocument:\n\"\"\"\n{{document}}\n\"\"\""]].forEach(function (p) {
      var b = el("button", "btn btn-sm", p[0]); b.type = "button";
      b.addEventListener("click", function () { ta.value = p[1]; draw3(); });
      samples.appendChild(b);
    });
    box3.appendChild(samples); box3.appendChild(ta); box3.appendChild(res); box3.appendChild(score);
    pl.appendChild(box3);

    function draw3() {
      var t = ta.value, hit = 0;
      res.innerHTML = "";
      CHECKS.forEach(function (c) {
        var ok = c.test.test(t);
        if (ok) hit++;
        var row = el("div", "flex items-center gap-2 text-sm " + (ok ? "text-good" : "text-ink-600"));
        row.appendChild(el("span", "font-mono", ok ? "✓" : "○"));
        row.appendChild(el("span", ok ? "" : "text-ink-400", c.label));
        res.appendChild(row);
      });
      score.textContent = hit + " of " + CHECKS.length + " structural properties present.";
      score.className = "text-sm font-semibold " + (hit >= 5 ? "text-good" : hit >= 3 ? "text-warm" : "text-bad");
    }
    ta.addEventListener("input", draw3);
    draw3();
  }
})();
