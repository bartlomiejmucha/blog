/* Lesson 6 — head dimension calculator + per-head patterns */
(function () {
  var C = LC.Viz.C;
  var V = LC.Viz, el = LC.el;

  var root = document.getElementById("viz-heads");
  if (root) {
    var d = 4096, h = 32, kv = 32;
    var box = el("div", "grid gap-4 sm:grid-cols-2");
    var ctrl = el("div", "space-y-3");
    var out = el("div", "");
    box.appendChild(ctrl); box.appendChild(out);
    root.appendChild(box);

    // Each select keeps a setOptions so the head lists can be rebuilt: only head
    // counts that divide d_model give a whole d_head, and only KV-head counts
    // that divide the query-head count form equal GQA groups.
    function sel(label, cb) {
      var w = el("div", "space-y-1");
      w.appendChild(el("p", "text-xs text-ink-400", label));
      var s = document.createElement("select");
      s.className = "field";
      s.addEventListener("change", function () { cb(parseInt(s.value, 10)); });
      w.appendChild(s);
      w.setOptions = function (opts, val) {
        s.innerHTML = "";
        opts.forEach(function (o) { var n = document.createElement("option"); n.value = n.textContent = o; s.appendChild(n); });
        s.value = val;
      };
      return w;
    }
    function divisorsOf(total, candidates) {
      return candidates.filter(function (c) { return total % c === 0; });
    }
    var HEAD_CHOICES = [8, 12, 16, 32, 64];
    var KV_CHOICES = [1, 2, 4, 8, 16, 32, 64];

    var selD = sel("d_model", function (v) { d = v; syncHeads(); draw(); });
    var selH = sel("query heads", function (v) { h = v; syncKV(); draw(); });
    var selKV = sel("key/value heads (GQA groups)", function (v) { kv = v; draw(); });
    ctrl.appendChild(selD); ctrl.appendChild(selH); ctrl.appendChild(selKV);

    function syncKV() {
      var opts = divisorsOf(h, KV_CHOICES);
      if (opts.indexOf(kv) === -1) kv = opts[opts.length - 1];
      selKV.setOptions(opts, kv);
    }
    function syncHeads() {
      var opts = divisorsOf(d, HEAD_CHOICES);
      if (opts.indexOf(h) === -1) h = opts[opts.length - 1];
      selH.setOptions(opts, h);
      syncKV();
    }
    selD.setOptions([768, 1024, 2048, 4096, 8192], d);
    syncHeads();

    function draw() {
      var dh = d / h;
      var qkvo = 2 * d * d + 2 * (d * (kv * dh));
      out.innerHTML =
        '<div class="rounded-lg border border-ink-700 bg-ink-850 p-3 font-mono text-xs space-y-1.5">' +
        '<p class="text-ink-400">d_head = d_model / n_heads</p>' +
        '<p class="text-ink-100">= ' + d + " / " + h + " = <span class='text-accent'>" + dh + "</span></p>" +
        '<hr class="border-ink-700">' +
        "<p>W_Q: [" + d + " → " + (h * dh) + "]</p>" +
        "<p>W_K: [" + d + " → " + (kv * dh) + "]" + (kv < h ? ' <span class="text-good">(shrunk by GQA)</span>' : "") + "</p>" +
        "<p>W_V: [" + d + " → " + (kv * dh) + "]</p>" +
        "<p>W_O: [" + (h * dh) + " → " + d + "]</p>" +
        '<hr class="border-ink-700">' +
        '<p class="text-ink-100">attention params ≈ ' + (qkvo / 1e6).toFixed(1) + "M per layer</p>" +
        '<p class="text-ink-400">KV cache per token per layer: ' + (2 * kv * dh * 2 / 1024).toFixed(1) + " KB (fp16)</p>" +
        "</div>" +
        '<p class="mt-2 text-xs text-ink-400">' +
        (dh < 32 ? "d_head is very small here — heads this narrow struggle to represent anything useful."
          : kv < h ? "With " + kv + " KV heads instead of " + h + ", the cache shrinks " + (h / kv) + "×."
          : "Full multi-head: every query head has its own key and value head, and the cache is at its largest.") + "</p>";
    }
    draw();
  }

  /* ---- per-head patterns ---- */
  var hp = document.getElementById("viz-head-patterns");
  if (hp) {
    var words = "When Mary and John went to the store John gave a drink to".split(" ");
    var n = words.length;
    var HEADS = [
      { name: "Head 3 — previous token", f: function (i, j) { return j === i - 1 ? 4 : (j === i ? 0.5 : 0); } },
      { name: "Head 7 — attention sink", f: function (i, j) { return j === 0 ? 4 : (j === i ? 1 : 0.1); } },
      { name: "Head 11 — duplicate token", f: function (i, j) { return words[j] === words[i] && j < i ? 4 : (j === i ? 1 : 0.1); } },
      // Gated on the final position: "to" also occurs at "went to the store",
      // and firing there would not be name-mover behaviour.
      { name: "Head 14 — induction / name mover", f: function (i, j) { return (i === n - 1 && words[j] === "Mary") ? 4 : (j === i - 1 ? 1 : 0.2); } }
    ];
    var wrap = el("div", "grid gap-4 sm:grid-cols-2");
    HEADS.forEach(function (H) {
      var card = el("div", "figure");
      card.appendChild(el("p", "figure-title", H.name));
      var g = el("div", "inline-grid gap-[2px]");
      g.style.gridTemplateColumns = "repeat(" + n + ", 0.85rem)";
      for (var i = 0; i < n; i++) {
        var raw = [];
        for (var j = 0; j < n; j++) raw.push(j > i ? -1e9 : H.f(i, j));
        var p = V.softmax(raw);
        for (var j2 = 0; j2 < n; j2++) {
          var c = el("div", "h-3.5 rounded-[2px]");
          c.style.background = j2 > i ? C.void : V.heat(Math.pow(p[j2], 0.6));
          c.title = words[i] + " → " + words[j2];
          g.appendChild(c);
        }
      }
      card.appendChild(g);
      card.appendChild(el("p", "mt-2 text-xs text-ink-400", "Same sentence, same layer, completely different behaviour."));
      wrap.appendChild(card);
    });
    hp.appendChild(wrap);
  }
})();
