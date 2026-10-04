/* Lesson 1 — life of a request, step by step */
(function () {
  var V = LC.Viz, C = V.C, el = LC.el;
  var host = document.getElementById("viz-lifecycle");
  if (!host) return;

  var STAGES = [
    { name: "HTTP", where: "Sources/serve", what: "Hummingbird parses the JSON body.", client: "Request sent. Waiting." },
    { name: "Template", where: "LoadedModel.prompt", what: "Messages become one string, then token ids: [151644, 872, 198, ...].", client: "Waiting." },
    { name: "Queue", where: "Engine inbox", what: "The job waits for the worker thread. A full queue answers 429 at once.", client: "Waiting." },
    { name: "Prefill", where: "worker thread", what: "One forward pass over the whole prompt fills the caches and yields the first token.", client: "Waiting. This is most of the time to first token." },
    { name: "Decode", where: "worker thread", what: "One forward pass per new token, each reading every weight once.", client: "Text is streaming in." },
    { name: "Stream", where: "Detokenizer + SSE", what: "Token ids become text; each piece goes out as a server-sent event.", client: "data: {\"delta\":{\"content\":\" blue\"}} ..." }
  ];

  var step = 0;
  var box = el("div", "space-y-4");
  var row = el("div", "grid grid-cols-3 gap-2 sm:grid-cols-6");
  var cells = STAGES.map(function (s, i) {
    var c = el("div", "rounded-lg border px-2 py-3 text-center text-xs transition");
    c.appendChild(el("div", "font-semibold", (i + 1) + ". " + s.name));
    c.appendChild(el("div", "mt-1 font-mono text-[10px] text-ink-400", s.where));
    row.appendChild(c);
    return c;
  });
  var detail = el("div", "card-tight space-y-1 text-sm");
  var what = el("p", "text-ink-100");
  var client = el("p", "font-mono text-xs text-ink-400");
  detail.appendChild(what); detail.appendChild(client);
  var nav = el("div", "flex gap-2");
  var prev = el("button", "btn btn-sm", "← Back"); prev.type = "button";
  var next = el("button", "btn btn-sm btn-primary", "Next →"); next.type = "button";
  nav.appendChild(prev); nav.appendChild(next);
  box.appendChild(row); box.appendChild(detail); box.appendChild(nav);
  host.appendChild(box);

  function paint() {
    cells.forEach(function (c, i) {
      c.style.borderColor = i === step ? C.accent : C.grid;
      c.style.opacity = i <= step ? "1" : "0.45";
      c.style.background = i === step ? "color-mix(in srgb, " + C.accent + " 14%, transparent)" : "transparent";
    });
    what.textContent = STAGES[step].what;
    client.textContent = "Client sees: " + STAGES[step].client;
    prev.disabled = step === 0;
    next.disabled = step === STAGES.length - 1;
  }
  prev.addEventListener("click", function () { step = Math.max(0, step - 1); paint(); });
  next.addEventListener("click", function () { step = Math.min(STAGES.length - 1, step + 1); paint(); });
  paint();
})();
