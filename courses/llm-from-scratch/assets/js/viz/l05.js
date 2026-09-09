/* Lesson 5 — attention heatmap */
(function () {
  var C = LC.Viz.C;
  var V = LC.Viz, el = LC.el;
  var root = document.getElementById("viz-attention");
  if (!root) return;

  var SENTENCES = {
    "The trophy did not fit in the suitcase because it was too big":
      { it: ["trophy"], was: ["it"], big: ["trophy", "was"] },
    "The keys to the cabinet are on the table":
      { are: ["keys"], on: ["are"], table: ["the", "on"] },
    "Alice gave Bob a book because she owed him one":
      { she: ["Alice"], him: ["Bob"], one: ["book"] }
  };

  var box = el("div", "space-y-4");
  var pick = el("div", "flex flex-wrap gap-2");
  var grid = el("div", "overflow-x-auto");
  var info = el("p", "text-xs text-ink-400");
  box.appendChild(pick); box.appendChild(grid); box.appendChild(info);
  root.appendChild(box);

  var current = Object.keys(SENTENCES)[0];
  var focus = -1;

  function scores(words, links) {
    // Build plausible pseudo-scores: self, previous token, an attention sink, plus semantic links.
    var n = words.length;
    var M = [];
    for (var i = 0; i < n; i++) {
      var row = [];
      for (var j = 0; j < n; j++) {
        if (j > i) { row.push(-Infinity); continue; }
        var s = 0.2;
        if (j === i) s += 1.4;
        if (j === i - 1) s += 1.1;
        if (j === 0) s += 0.9;                       // attention sink
        var w = words[i].toLowerCase().replace(/[^a-z]/g, "");
        if (links[w] && links[w].indexOf(words[j].toLowerCase()) !== -1) s += 3.2;
        row.push(s);
      }
      M.push(V.softmax(row.map(function (v) { return v === -Infinity ? -1e9 : v; })));
      for (var j2 = i + 1; j2 < n; j2++) M[i][j2] = 0;
    }
    return M;
  }

  function draw() {
    var words = current.split(" ");
    var M = scores(words, SENTENCES[current]);
    var n = words.length;
    var t = document.createElement("table");
    t.className = "border-separate text-[10px]";
    t.style.borderSpacing = "2px";

    var head = t.insertRow();
    head.insertCell().outerHTML = '<th class="p-1"></th>';
    words.forEach(function (w) {
      head.insertCell().outerHTML = '<th class="p-1 align-bottom font-mono text-ink-400" style="writing-mode:vertical-rl;transform:rotate(180deg);height:4.5rem">' + w + "</th>";
    });

    for (var i = 0; i < n; i++) {
      var tr = t.insertRow();
      tr.insertCell().outerHTML = '<th class="pr-2 text-right font-mono ' +
        (i === focus ? "text-accent" : "text-ink-400") + '">' + words[i] + "</th>";
      for (var j = 0; j < n; j++) {
        var td = tr.insertCell();
        var v = M[i][j];
        td.className = "h-6 w-6 rounded text-center align-middle";
        td.style.background = j > i ? C.void : V.heat(Math.pow(v, 0.6));
        td.style.opacity = (focus === -1 || focus === i) ? 1 : 0.25;
        td.title = words[i] + " → " + words[j] + " : " + (v * 100).toFixed(1) + "%";
        if (j > i) td.style.border = "1px dashed " + C.grid;
        (function (i) { td.addEventListener("mouseenter", function () { if (focus !== i) { focus = i; draw(); } }); })(i);
      }
    }
    grid.innerHTML = "";
    grid.appendChild(t);

    if (focus >= 0) {
      var row = M[focus].map(function (v, j) { return [words[j], v]; })
        .sort(function (a, b) { return b[1] - a[1]; }).slice(0, 3);
      info.innerHTML = 'Query position <span class="text-accent font-mono">' + words[focus] +
        "</span> puts most of its weight on: " +
        row.map(function (r) { return '<span class="font-mono text-ink-100">' + r[0] + "</span> " + (r[1] * 100).toFixed(0) + "%"; }).join(", ") +
        ". Row sums to 1. The dashed cells are masked — those positions are in the future.";
    } else {
      info.textContent = "Rows are queries, columns are keys. Hover a row. The upper-right triangle is masked out by the causal mask.";
    }
  }

  Object.keys(SENTENCES).forEach(function (s) {
    var b = el("button", "btn btn-sm" + (s === current ? " btn-primary" : ""), s.split(" ").slice(0, 4).join(" ") + "…");
    b.type = "button";
    b.addEventListener("click", function () {
      current = s; focus = -1;
      LC.$$("button", pick).forEach(function (n) { n.classList.remove("btn-primary"); });
      b.classList.add("btn-primary"); draw();
    });
    pick.appendChild(b);
  });
  draw();
})();
