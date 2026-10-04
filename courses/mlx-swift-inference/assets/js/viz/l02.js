/* Lesson 2 — decode speed ceiling from bandwidth and model size */
(function () {
  var V = LC.Viz, C = V.C, el = LC.el;
  var host = document.getElementById("viz-bandwidth");
  if (!host) return;

  // Advertised unified-memory bandwidth, GB/s.
  var CHIPS = [["M1", 68], ["M2 / M3", 100], ["M4", 120], ["M3 Pro", 150], ["M1/M2 Pro", 200],
               ["M4 Pro", 273], ["M1/M2 Max", 400], ["M4 Max", 546], ["M1/M2 Ultra", 800]];
  var BITS = [["4-bit (4.5 effective)", 4.5], ["8-bit (8.5 effective)", 8.5], ["bf16", 16]];
  var EFF = 0.75;

  var box = el("div", "space-y-4");
  var controls = el("div", "grid gap-3 sm:grid-cols-3");
  function select(label, options, initial) {
    var wrap = el("label", "space-y-1 text-xs text-ink-400");
    wrap.appendChild(el("span", "", label));
    var s = document.createElement("select");
    s.className = "field";
    options.forEach(function (o, i) {
      var opt = document.createElement("option");
      opt.value = i; opt.textContent = o[0]; s.appendChild(opt);
    });
    s.value = initial;
    wrap.appendChild(s); controls.appendChild(wrap);
    return s;
  }
  var chip = select("Chip", CHIPS, 0);
  var bits = select("Weights", BITS, 0);
  var pwrap = el("label", "space-y-1 text-xs text-ink-400");
  var plab = el("span", "", "");
  var params = document.createElement("input");
  params.type = "range"; params.className = "slider"; params.min = 0; params.max = 100; params.value = 0;
  pwrap.appendChild(plab); pwrap.appendChild(params); controls.appendChild(pwrap);

  var bar = el("div", "bar-track h-4");
  var fill = el("div", "bar-fill");
  bar.appendChild(fill);
  var result = el("p", "font-mono text-sm text-ink-100");
  var note = el("p", "text-xs text-ink-400");
  box.appendChild(controls); box.appendChild(result); box.appendChild(bar); box.appendChild(note);
  host.appendChild(box);

  // Slider maps to 0.8B .. 70B on a log scale.
  function paramsB() { return 0.8 * Math.pow(70 / 0.8, params.value / 100); }

  function paint() {
    var p = paramsB();
    plab.textContent = "Parameters: " + (p < 10 ? p.toFixed(1) : p.toFixed(0)) + "B";
    var bw = CHIPS[chip.value][1], b = BITS[bits.value][1];
    var gb = p * b / 8;
    var tps = bw * EFF / gb;
    result.textContent = gb.toFixed(2) + " GB per token → ceiling ≈ " + tps.toFixed(tps < 10 ? 1 : 0) + " tokens/s";
    fill.style.width = Math.min(100, tps / 2) + "%";
    fill.style.background = tps < 10 ? C.bad : tps < 30 ? C.warm : C.accent;
    var msg = "Bar is full at 200 tokens/s. ";
    if (chip.value === "0" && p < 1 && bits.value === "0") msg += "Measured on an M1 with Qwen3.5-0.8B at 4 bits: about 90 tokens/s. The rest goes to the output projection, attention and per-step overhead.";
    else if (chip.value === "0" && gb > 5.5) msg += "This model does not fit in an 8 GB M1 alongside the OS.";
    else msg += "Real servers land below the ceiling; the rule tells you where the ceiling is.";
    note.textContent = msg;
  }
  [chip, bits].forEach(function (s) { s.addEventListener("change", paint); });
  params.addEventListener("input", paint);
  paint();
})();
