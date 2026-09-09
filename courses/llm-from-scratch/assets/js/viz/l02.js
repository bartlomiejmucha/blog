/* Lesson 2 — BPE trainer + live tokenizer */
(function () {
  var V = LC.Viz, el = LC.el;

  /* ---------- BPE trainer ---------- */
  var root = document.getElementById("viz-bpe");
  if (root) {
    var box = el("div", "space-y-3");
    var ta = document.createElement("textarea");
    ta.className = "field h-20 leading-6";
    ta.value = "low low low low low lower lower newest newest newest widest widest";
    var ctrls = el("div", "flex flex-wrap gap-2");
    var stepB = el("button", "btn btn-sm btn-primary", "Run one merge");
    var run5 = el("button", "btn btn-sm", "Run 5 merges");
    var resetB = el("button", "btn btn-sm", "Reset");
    [stepB, run5, resetB].forEach(function (b) { b.type = "button"; ctrls.appendChild(b); });
    var view = el("div", "space-y-2");
    var rules = el("div", "space-y-1");
    box.appendChild(ta); box.appendChild(ctrls); box.appendChild(view); box.appendChild(rules);
    root.appendChild(box);

    var words, merges;

    function init() {
      words = {};
      ta.value.trim().split(/\s+/).forEach(function (w) {
        var key = w.split("").join(" ") + " </w>";
        words[key] = (words[key] || 0) + 1;
      });
      merges = [];
      draw();
    }

    function pairCounts() {
      var counts = {};
      Object.keys(words).forEach(function (w) {
        var syms = w.split(" ");
        for (var i = 0; i < syms.length - 1; i++) {
          var p = syms[i] + " " + syms[i + 1];
          counts[p] = (counts[p] || 0) + words[w];
        }
      });
      return counts;
    }

    function merge() {
      var counts = pairCounts();
      var best = null, bestN = 0;
      Object.keys(counts).forEach(function (p) { if (counts[p] > bestN) { bestN = counts[p]; best = p; } });
      if (!best || bestN < 2) return false;
      var out = {};
      var joined = best.replace(" ", "");
      var pair = best.split(" ");
      Object.keys(words).forEach(function (w) {
        // Walk the symbol list rather than string-replacing: adjacent occurrences
        // of the same pair share a separator space, so split/join would merge
        // only the first of them ("a b a b" → "ab a b").
        var syms = w.split(" "), next = [];
        for (var i = 0; i < syms.length; i++) {
          if (syms[i] === pair[0] && syms[i + 1] === pair[1]) { next.push(joined); i++; }
          else next.push(syms[i]);
        }
        var nw = next.join(" ");
        out[nw] = (out[nw] || 0) + words[w];
      });
      words = out;
      merges.push({ pair: best, count: bestN, result: joined });
      return true;
    }

    function draw() {
      view.innerHTML = "";
      var head = el("p", "text-xs text-ink-400",
        "Current split of each distinct word (× frequency). </w> marks a word boundary.");
      view.appendChild(head);
      var list = el("div", "flex flex-wrap gap-2");
      Object.keys(words).forEach(function (w) {
        var chip = el("div", "rounded-lg border border-ink-700 bg-ink-850 px-2 py-1");
        var inner = el("div", "flex flex-wrap items-center gap-1");
        w.split(" ").forEach(function (s) {
          inner.appendChild(el("span", "tok border-ink-600 text-accent", s));
        });
        inner.appendChild(el("span", "font-mono text-[10px] text-ink-600", "×" + words[w]));
        chip.appendChild(inner);
        list.appendChild(chip);
      });
      view.appendChild(list);

      var counts = pairCounts();
      var top = Object.keys(counts).sort(function (a, b) { return counts[b] - counts[a]; }).slice(0, 5);
      var pc = el("p", "text-xs text-ink-400", "Most frequent adjacent pairs right now: " +
        (top.length ? top.map(function (p) { return "‹" + p.replace(" ", "·") + "› " + counts[p]; }).join(" · ") : "none left"));
      view.appendChild(pc);

      rules.innerHTML = "";
      if (merges.length) {
        rules.appendChild(el("p", "text-xs font-semibold text-ink-100", "Learned merge rules, in order:"));
        merges.forEach(function (m, i) {
          rules.appendChild(el("p", "font-mono text-xs text-ink-300",
            (i + 1) + ". " + m.pair.replace(" ", " + ") + " → " + m.result + "   (seen " + m.count + "×)"));
        });
      }
    }

    stepB.addEventListener("click", function () { if (!merge()) alert("No pair occurs more than once — training is done."); draw(); });
    run5.addEventListener("click", function () { for (var i = 0; i < 5; i++) if (!merge()) break; draw(); });
    resetB.addEventListener("click", init);
    ta.addEventListener("change", init);
    init();
  }

  /* ---------- live tokenizer (real cl100k_base ids) ---------- */
  var tk = document.getElementById("viz-tokenize");
  if (tk) {
    // A cut-down cl100k_base rank table (see l02-vocab.js): the low-id core of
    // the vocabulary plus every token the presets need. The merge loop below is
    // the real BPE algorithm, so the presets reproduce tiktoken exactly. Text
    // outside them splits more finely than the full 100k vocabulary would,
    // because the rarer merges were left out of the table.
    var RANKS = window.CL100K_SUBSET || {};

    // cl100k_base pre-tokenizer pattern. Text is split here first, which is why
    // a token can hold a leading space but never an interior one.
    var PAT = /'[sS]|'[tT]|'[rR][eE]|'[vV][eE]|'[mM]|'[lL][lL]|'[dD]|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}{1,3}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+/gu;

    var enc = new TextEncoder();
    var dec = new TextDecoder("utf-8", { fatal: true });

    // UTF-8 bytes, one byte per character, so merge keys match the table.
    function toBytes(s) {
      var u = enc.encode(s), o = "";
      for (var i = 0; i < u.length; i++) o += String.fromCharCode(u[i]);
      return o;
    }

    function fromBytes(k) {
      var u = new Uint8Array(k.length);
      for (var i = 0; i < k.length; i++) u[i] = k.charCodeAt(i);
      try { return dec.decode(u); } catch (e) { return "▯"; }  // lone byte of a multi-byte char
    }

    // Byte-pair merging: repeatedly join the adjacent pair with the lowest rank.
    function bpe(piece) {
      var parts = piece.split("");
      while (parts.length > 1) {
        var best = Infinity, at = -1;
        for (var i = 0; i < parts.length - 1; i++) {
          var r = RANKS[parts[i] + parts[i + 1]];
          if (r !== undefined && r < best) { best = r; at = i; }
        }
        if (at < 0) break;
        parts.splice(at, 2, parts[at] + parts[at + 1]);
      }
      return parts;
    }

    function encode(text) {
      var out = [], m;
      PAT.lastIndex = 0;
      while ((m = PAT.exec(text)) !== null) {
        if (m[0] === "") break;
        bpe(toBytes(m[0])).forEach(function (k) { out.push({ text: fromBytes(k), id: RANKS[k] }); });
      }
      return out;
    }

    var b2 = el("div", "space-y-3");
    var input = document.createElement("textarea");
    input.className = "field h-24 leading-6";
    input.value = "strawberry  strawberry";
    var presets = el("div", "flex flex-wrap gap-2");
    [["leading space", "strawberry  strawberry"],
     ["dog vs  dog", "dog dog"],
     ["trailing space", "The answer is "],
     ["numbers", "The total was 1234 in 2024."],
     ["code", "def add(a, b):\n    return a + b"],
     ["other script", "こんにちは世界"]].forEach(function (p) {
      var b = el("button", "btn btn-sm", p[0]); b.type = "button";
      b.addEventListener("click", function () { input.value = p[1]; render(); });
      presets.appendChild(b);
    });
    var out = el("div", "flex flex-wrap gap-1 rounded-lg border border-ink-700 bg-ink-850 p-3");
    var stat = el("p", "text-xs text-ink-400");
    b2.appendChild(presets); b2.appendChild(input); b2.appendChild(out); b2.appendChild(stat);
    tk.appendChild(b2);

    function render() {
      var toks = encode(input.value);
      out.innerHTML = "";
      toks.forEach(function (t) {
        var hue = (t.id * 137) % 360;
        var chip = el("span", "tok");
        chip.style.background = "hsl(" + hue + (V.light ? " 62% 90%)" : " 45% 20%)");
        chip.style.borderColor = "hsl(" + hue + (V.light ? " 45% 70%)" : " 45% 40%)");
        chip.innerHTML = '<span class="text-ink-100">' +
          t.text.replace(/ /g, "␣").replace(/\n/g, "⏎").replace(/&/g, "&amp;").replace(/</g, "&lt;") +
          '</span><span class="ml-1 text-[10px] text-ink-400">' + t.id + "</span>";
        out.appendChild(chip);
      });
      var chars = input.value.length;
      stat.textContent = toks.length + " tokens for " + chars + " characters (" +
        (chars / Math.max(toks.length, 1)).toFixed(2) + " chars per token). " +
        "Ids are the real cl100k_base ones GPT-4 uses. ␣ marks a leading space that belongs to the token. " +
        "The presets match the real tokenizer exactly; other text splits a little finer, " +
        "because this demo carries only the common core of the vocabulary.";
    }
    input.addEventListener("input", render);
    render();
  }
})();
