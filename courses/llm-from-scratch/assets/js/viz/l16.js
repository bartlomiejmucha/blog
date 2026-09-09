/* Lesson 16 — retrieval simulator + reliability compounding */
(function () {
  var V = LC.Viz, el = LC.el;

  var rag = document.getElementById("viz-rag");
  if (rag) {
    var DOCS = [
      "Refunds are issued within 14 days of the return being received at our warehouse.",
      "To return an item, request a label from your account page within 30 days of delivery.",
      "Damaged goods should be reported with photographs within 48 hours of delivery.",
      "Our support team is available Monday to Friday, 9am to 6pm UK time.",
      "Error code ERR_5521 means the payment provider declined the transaction; retry with a different card.",
      "Gift cards are non-refundable and cannot be exchanged for cash."
    ];
    // Without stopword removal every score collapses: "can I return a gift card"
    // matched the ERR_5521 chunk on the word "a".
    var STOP = ("a an and are as at be being by can cannot do does for from how i if in is it its my " +
      "of on or our should the their then there to until up was what when where which who will with " +
      "within your you").split(" ");
    function vec(s) {
      var words = (s.toLowerCase().match(/[a-z_0-9]+/g) || [])
        .filter(function (w) { return STOP.indexOf(w) === -1; });
      var v = {};
      words.forEach(function (w) { v[w] = (v[w] || 0) + 1; });
      return v;
    }
    function cos(a, b) {
      var dot = 0, na = 0, nb = 0;
      Object.keys(a).forEach(function (k) { na += a[k] * a[k]; if (b[k]) dot += a[k] * b[k]; });
      Object.keys(b).forEach(function (k) { nb += b[k] * b[k]; });
      return na && nb ? dot / Math.sqrt(na * nb) : 0;
    }
    var box = el("div", "space-y-3");
    var qin = document.createElement("input");
    qin.className = "field"; qin.value = "how many days until refunds are issued";
    var qs = el("div", "flex flex-wrap gap-2");
    [["wording matches", "how many days until refunds are issued"],
     ["rare exact string", "what does ERR_5521 mean"],
     ["paraphrase — misses", "how long until I get my money back"]].forEach(function (q) {
      var b = el("button", "btn btn-sm", q[0]); b.type = "button";
      b.title = q[1];
      b.addEventListener("click", function () { qin.value = q[1]; draw(); });
      qs.appendChild(b);
    });
    var rank = el("div", "space-y-1.5");
    var prompt = el("pre", "whitespace-pre-wrap rounded-lg border border-ink-700 bg-ink-850 p-3 font-mono text-[11px] leading-5 text-ink-300");
    var note = el("p", "text-xs text-ink-400");
    box.appendChild(qs); box.appendChild(qin); box.appendChild(rank);
    box.appendChild(el("p", "text-xs font-semibold text-ink-100", "Assembled prompt sent to the model:"));
    box.appendChild(prompt); box.appendChild(note);
    rag.appendChild(box);

    function draw() {
      var qv = vec(qin.value);
      var scored = DOCS.map(function (d, i) { return { d: d, i: i, s: cos(qv, vec(d)) }; })
        .sort(function (a, b) { return b.s - a.s; });
      rank.innerHTML = "";
      scored.forEach(function (r, idx) {
        var kept = idx < 2 && r.s > 0;
        var row = el("div", "flex items-start gap-2 rounded-lg border px-2 py-1.5 text-xs " +
          (kept ? "border-good/50 bg-good/5 text-ink-100" : "border-ink-800 text-ink-600"));
        row.appendChild(el("span", "shrink-0 font-mono " + (kept ? "text-good" : "text-ink-600"), r.s.toFixed(3)));
        row.appendChild(el("span", "", r.d));
        rank.appendChild(row);
      });
      var top = scored.filter(function (r, i) { return i < 2 && r.s > 0; });
      prompt.textContent = "Answer the question using only the context below.\n" +
        "If the context does not contain the answer, say \"I don't know\".\n\n" +
        "Context:\n" + (top.length ? top.map(function (r, i) { return "[" + (i + 1) + "] " + r.d; }).join("\n") : "(nothing retrieved)") +
        "\n\nQuestion: " + qin.value + "\nAnswer:";
      note.textContent = scored[0].s === 0
        ? "Nothing matched, and the answer was sitting in the corpus the whole time. This demo scores by word overlap, and the question shares no words with \u201cRefunds are issued within 14 days\u201d. A neural embedding would catch it, because the two mean the same thing. That is the case dense retrieval exists for — and note the assembled prompt still behaves correctly, telling the model to say it does not know rather than invent."
        : "This demo scores by word overlap. A real system embeds both query and chunks with a neural encoder, which catches paraphrases word overlap misses \u2014 and misses exact rare strings like ERR_5521 that word matching nails. That is why production systems run both.";
    }
    qin.addEventListener("input", draw);
    draw();
  }

  var ag = document.getElementById("viz-agent");
  if (ag) {
    var rel = 0.95, steps = 20;
    var box2 = el("div", "space-y-3");
    function sl(label, min, max, step, val, unit, cb) {
      var w = el("div", "space-y-1");
      var t = el("div", "flex justify-between text-xs");
      t.appendChild(el("span", "text-ink-400", label));
      var o = el("span", "font-mono text-accent", val + unit);
      t.appendChild(o);
      var i = document.createElement("input");
      i.type = "range"; i.min = min; i.max = max; i.step = step; i.value = val; i.className = "slider";
      i.addEventListener("input", function () { o.textContent = i.value + unit; cb(parseFloat(i.value)); });
      w.appendChild(t); w.appendChild(i); return w;
    }
    var chain = el("div", "flex flex-wrap gap-1");
    var out = el("div", "rounded-lg border border-ink-700 bg-ink-850 p-3 font-mono text-sm");
    var note2 = el("p", "text-xs text-ink-400");
    box2.appendChild(sl("per-step reliability", 0.5, 0.999, 0.001, rel, "", function (v) { rel = v; draw2(); }));
    box2.appendChild(sl("steps in the task", 1, 50, 1, steps, "", function (v) { steps = v; draw2(); }));
    box2.appendChild(chain); box2.appendChild(out); box2.appendChild(note2);
    ag.appendChild(box2);

    function draw2() {
      var p = Math.pow(rel, steps);
      chain.innerHTML = "";
      for (var i = 0; i < steps; i++) {
        var d = el("div", "h-3 w-3 rounded-[2px]");
        d.style.background = V.heat(Math.pow(rel, i + 1));
        chain.appendChild(d);
      }
      out.innerHTML = "<span class='text-ink-400'>P(all " + steps + " steps correct) = " + rel.toFixed(3) + "^" + steps + " = </span>" +
        "<span class='" + (p > 0.8 ? "text-good" : p > 0.5 ? "text-warm" : "text-bad") + "'>" + (p * 100).toFixed(1) + "%</span>";
      note2.textContent = p < 0.5
        ? "The task fails more often than it succeeds. This is why long autonomous chains need verification between steps rather than a better model alone."
        : "Reasonable — but notice how fast this falls as you add steps. Going from 10 to 30 steps at the same reliability is not a small change.";
    }
    draw2();
  }
})();
