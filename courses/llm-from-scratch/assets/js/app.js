/* Shared runtime: progress storage, exercise engine, navigation. */
(function () {
  "use strict";

  var KEY = "llm-course-v1";
  var LESSONS = window.COURSE ? window.COURSE.lessons : [];

  /* ---------- storage ---------- */

  function emptyState() {
    return { version: 1, lessons: {}, updated: Date.now() };
  }

  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return emptyState();
      var s = JSON.parse(raw);
      if (!s || typeof s !== "object" || !s.lessons) return emptyState();
      return s;
    } catch (e) {
      return emptyState();
    }
  }

  function save(s) {
    s.updated = Date.now();
    try {
      localStorage.setItem(KEY, JSON.stringify(s));
    } catch (e) {
      /* private mode, quota — progress is a convenience, never block the page */
    }
  }

  var state = load();

  function lessonState(id) {
    if (!state.lessons[id]) state.lessons[id] = { visited: false, read: false, ex: {} };
    if (!state.lessons[id].ex) state.lessons[id].ex = {};
    return state.lessons[id];
  }

  var Progress = {
    all: function () { return state; },
    lesson: lessonState,
    visit: function (id) { lessonState(id).visited = true; save(state); },
    markRead: function (id, v) { lessonState(id).read = !!v; save(state); },
    setExercise: function (id, exId, correct) {
      lessonState(id).ex[exId] = !!correct;
      save(state);
    },
    exerciseCount: function (id) {
      var ex = lessonState(id).ex, n = 0;
      for (var k in ex) if (ex[k]) n++;
      return n;
    },
    reset: function () { state = emptyState(); save(state); },
    export: function () { return JSON.stringify(state, null, 2); },
    import: function (json) {
      var s = JSON.parse(json);
      if (!s.lessons) throw new Error("not a progress file");
      state = s; save(state);
    }
  };

  /* lesson is "complete" when it was read and every exercise on it is solved */
  function lessonComplete(meta) {
    var st = lessonState(meta.id);
    if (!st.read) return false;
    return Progress.exerciseCount(meta.id) >= meta.exercises;
  }

  function courseStats() {
    var doneEx = 0, totalEx = 0, doneLessons = 0;
    LESSONS.forEach(function (m) {
      totalEx += m.exercises;
      doneEx += Math.min(Progress.exerciseCount(m.id), m.exercises);
      if (lessonComplete(m)) doneLessons++;
    });
    return { doneEx: doneEx, totalEx: totalEx, doneLessons: doneLessons, totalLessons: LESSONS.length };
  }

  /* ---------- small helpers ---------- */

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function norm(s) {
    return String(s).toLowerCase().trim().replace(/[\s_-]+/g, " ").replace(/[.,!?"']/g, "");
  }
  function shuffleStable(arr) { return arr; }

  /* ---------- exercise engine ---------- */
  /*
    Markup contract:
      <div data-ex data-ex-id="1" data-ex-type="mcq" data-answer="2">
        <div data-ex-prompt>…</div>
        <div>            <!-- any wrapper; the engine queries [data-opt] directly -->
          <button data-opt="0">…</button> …
        </div>
        <div data-ex-explain hidden>…</div>
      </div>
    types: mcq | multi | numeric | fill | order
  */

  function buildExercise(node, lessonId) {
    var type = node.dataset.exType;
    var exId = node.dataset.exId;
    var saved = lessonState(lessonId).ex[exId];

    var footer = el("div", "mt-4 flex flex-wrap items-center gap-3");
    var check = el("button", "btn btn-primary btn-sm", "Check answer");
    var again = el("button", "btn btn-sm", "Try again");
    again.hidden = true;
    var verdict = el("span", "text-sm font-medium");
    footer.appendChild(check);
    footer.appendChild(again);
    footer.appendChild(verdict);
    node.appendChild(footer);

    var explain = $("[data-ex-explain]", node);

    function finish(correct) {
      verdict.textContent = correct ? "Correct" : "Not quite — read the explanation, then try again.";
      verdict.className = "text-sm font-medium " + (correct ? "text-good" : "text-bad");
      if (explain) explain.hidden = false;
      check.hidden = true;
      again.hidden = correct;
      Progress.setExercise(lessonId, exId, correct);
      renderLessonProgress();
    }

    function resetUI() {
      verdict.textContent = "";
      check.hidden = false;
      again.hidden = true;
      if (explain) explain.hidden = true;
    }

    var api = { check: function () { return false; }, reset: function () {} };

    if (type === "mcq" || type === "multi") {
      var multi = type === "multi";
      var answers = String(node.dataset.answer).split(",").map(function (s) { return s.trim(); });
      var opts = $$("[data-opt]", node);
      opts.forEach(function (b) {
        b.type = "button";
        b.className = "opt";
        b.addEventListener("click", function () {
          if (check.hidden) return;
          if (multi) {
            b.dataset.state = b.dataset.state === "selected" ? "" : "selected";
          } else {
            opts.forEach(function (o) { o.dataset.state = ""; });
            b.dataset.state = "selected";
          }
        });
      });
      api.check = function () {
        var picked = opts.filter(function (o) { return o.dataset.state === "selected"; })
                         .map(function (o) { return o.dataset.opt; });
        if (!picked.length) return null;
        var correct = picked.length === answers.length &&
          picked.every(function (p) { return answers.indexOf(p) !== -1; });
        opts.forEach(function (o) {
          var isAns = answers.indexOf(o.dataset.opt) !== -1;
          var wasPicked = o.dataset.state === "selected";
          o.dataset.state = isAns ? (wasPicked ? "correct" : "missed") : (wasPicked ? "wrong" : "");
        });
        return correct;
      };
      api.reset = function () { opts.forEach(function (o) { o.dataset.state = ""; }); };
    }

    else if (type === "numeric") {
      var target = parseFloat(node.dataset.answer);
      var tol = parseFloat(node.dataset.tolerance || "0.001");
      var input = el("input", "field max-w-xs");
      input.placeholder = node.dataset.placeholder || "your answer";
      input.inputMode = "decimal";
      node.insertBefore(input, footer);
      api.check = function () {
        var v = parseFloat(String(input.value).replace(",", "."));
        if (isNaN(v)) return null;
        return Math.abs(v - target) <= tol;
      };
      api.reset = function () { input.value = ""; input.focus(); };
    }

    else if (type === "fill") {
      var accepted = String(node.dataset.answer).split("|").map(norm);
      var inp = el("input", "field");
      inp.placeholder = node.dataset.placeholder || "type your answer";
      node.insertBefore(inp, footer);
      inp.addEventListener("keydown", function (e) { if (e.key === "Enter") check.click(); });
      api.check = function () {
        if (!inp.value.trim()) return null;
        return accepted.indexOf(norm(inp.value)) !== -1;
      };
      api.reset = function () { inp.value = ""; inp.focus(); };
    }

    else if (type === "order") {
      var listNode = $("[data-ex-order]", node);
      var items = $$("[data-item]", listNode);
      var correctOrder = items.map(function (i) { return i.dataset.item; }).slice().sort(function (a, b) {
        return Number(a) - Number(b);
      });
      // present shuffled, deterministically rotated so it never renders already-solved
      var shuffled = items.slice();
      shuffled.sort(function (a, b) { return (Number(a.dataset.item) * 7 % 11) - (Number(b.dataset.item) * 7 % 11); });
      shuffled.forEach(function (i) { listNode.appendChild(i); });

      function paint() {
        $$("[data-item]", listNode).forEach(function (i, idx) {
          $("[data-pos]", i).textContent = idx + 1;
        });
      }
      items.forEach(function (i) {
        i.className = "flex items-center gap-3 rounded-xl border border-ink-700 bg-ink-850/60 px-3 py-2 text-sm text-ink-300";
        var pos = el("span", "flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-ink-800 font-mono text-xs text-accent");
        pos.setAttribute("data-pos", "");
        i.insertBefore(pos, i.firstChild);
        var ctr = el("span", "ml-auto flex gap-1");
        var up = el("button", "btn btn-sm", "↑");
        var dn = el("button", "btn btn-sm", "↓");
        up.type = dn.type = "button";
        up.addEventListener("click", function () {
          var prev = i.previousElementSibling;
          if (prev) { listNode.insertBefore(i, prev); paint(); }
        });
        dn.addEventListener("click", function () {
          var next = i.nextElementSibling;
          if (next) { listNode.insertBefore(next, i); paint(); }
        });
        ctr.appendChild(up); ctr.appendChild(dn);
        i.appendChild(ctr);
      });
      paint();
      api.check = function () {
        var now = $$("[data-item]", listNode).map(function (i) { return i.dataset.item; });
        return now.join(",") === correctOrder.join(",");
      };
      api.reset = function () {};
    }

    check.addEventListener("click", function () {
      var r = api.check();
      if (r === null) { verdict.textContent = "Give it a shot first."; verdict.className = "text-sm text-ink-400"; return; }
      finish(r);
    });
    again.addEventListener("click", function () { api.reset(); resetUI(); });

    if (saved) {
      // Already solved in a previous session: show it as solved but let the learner redo it.
      var badge = el("span", "pill border-good/50 text-good", "solved earlier");
      footer.appendChild(badge);
      if (explain) explain.hidden = false;
    }
  }

  /* ---------- per-page chrome ---------- */

  function metaFor(id) {
    for (var i = 0; i < LESSONS.length; i++) if (LESSONS[i].id === id) return LESSONS[i];
    return null;
  }

  function renderLessonProgress() {
    var root = document.body;
    var id = root.dataset.lesson;
    if (!id) return;
    var meta = metaFor(id);
    if (!meta) return;
    var solved = Math.min(Progress.exerciseCount(id), meta.exercises);
    $$("[data-lesson-ex-count]").forEach(function (n) {
      n.textContent = solved + " / " + meta.exercises;
    });
    $$("[data-lesson-ex-bar]").forEach(function (n) {
      n.style.width = (meta.exercises ? (solved / meta.exercises) * 100 : 0) + "%";
    });
    var s = courseStats();
    $$("[data-course-bar]").forEach(function (n) {
      n.style.width = (s.doneEx / s.totalEx) * 100 + "%";
    });
    $$("[data-course-stat]").forEach(function (n) {
      n.textContent = s.doneLessons + " of " + s.totalLessons + " lessons complete · " +
        s.doneEx + "/" + s.totalEx + " exercises solved";
    });
  }

  function initLesson() {
    var id = document.body.dataset.lesson;
    if (!id) return;
    Progress.visit(id);

    $$("[data-ex]").forEach(function (n) { buildExercise(n, id); });

    var doneBtn = $("[data-mark-read]");
    if (doneBtn) {
      var st = lessonState(id);
      var paint = function () {
        doneBtn.textContent = st.read ? "✓ Marked as read" : "Mark lesson as read";
        doneBtn.classList.toggle("btn-primary", !st.read);
      };
      doneBtn.addEventListener("click", function () {
        st.read = !st.read;
        Progress.markRead(id, st.read);
        paint(); renderLessonProgress();
      });
      paint();
    }

    renderLessonProgress();

    document.addEventListener("keydown", function (e) {
      if (e.target && /input|textarea|select/i.test(e.target.tagName)) return;
      if (e.altKey || e.ctrlKey || e.metaKey) return;
      var next = $("[data-nav-next]"), prev = $("[data-nav-prev]");
      if (e.key === "ArrowRight" && next) next.click();
      if (e.key === "ArrowLeft" && prev) prev.click();
    });

    // Table of contents from h2 section headings
    var toc = $("[data-toc]");
    if (toc) {
      var heads = $$("main h2[id]");
      var links = [];
      heads.forEach(function (h, n) {
        var a = el("a", "toc-link flex gap-2 rounded px-2 py-1 text-xs text-ink-400 hover:bg-ink-800 hover:text-ink-100");
        a.href = "#" + h.id;
        a.appendChild(el("span", "shrink-0 font-mono text-ink-600", (n + 1) + "."));
        a.appendChild(el("span", "", h.textContent));
        toc.appendChild(a);
        links.push(a);
      });

      if (heads.length) {
        var active = -1;
        function setActive(i) {
          if (i === active) return;
          active = i;
          links.forEach(function (a, n) {
            var on = n === i;
            a.classList.toggle("bg-ink-800", on);
            a.classList.toggle("text-ink-100", on);
            a.classList.toggle("text-ink-400", !on);
            if (on) a.setAttribute("aria-current", "true");
            else a.removeAttribute("aria-current");
          });
        }
        function onScroll() {
          var i = 0;
          for (var n = 0; n < heads.length; n++) {
            if (heads[n].getBoundingClientRect().top <= 96) i = n;
          }
          if (window.innerHeight + window.scrollY >= document.body.scrollHeight - 4) i = heads.length - 1;
          setActive(i);
        }
        var ticking = false;
        window.addEventListener("scroll", function () {
          if (ticking) return;
          ticking = true;
          requestAnimationFrame(function () { ticking = false; onScroll(); });
        }, { passive: true });
        window.addEventListener("resize", onScroll, { passive: true });
        onScroll();
      }
    }
  }

  function initIndex() {
    var grid = $("[data-lesson-grid]");
    if (!grid) return;

    function render() {
      grid.innerHTML = "";
      var part = null;
      LESSONS.forEach(function (m) {
        if (m.part !== part) {
          part = m.part;
          var h = el("h2", "col-span-full mt-6 text-sm font-semibold uppercase tracking-widest text-ink-400", part);
          grid.appendChild(h);
        }
        var st = lessonState(m.id);
        var solved = Math.min(Progress.exerciseCount(m.id), m.exercises);
        var complete = lessonComplete(m);
        var a = el("a", "card group flex flex-col gap-3 transition hover:border-accent/60 hover:bg-ink-850/80");
        a.href = "lessons/" + m.file;

        var top = el("div", "flex items-start justify-between gap-3");
        top.appendChild(el("span", "pill font-mono", "Lesson " + m.num));
        var badge = el("span", "pill " + (complete ? "border-good/60 text-good" : st.visited ? "border-warm/60 text-warm" : ""),
          complete ? "complete" : st.visited ? "in progress" : "not started");
        top.appendChild(badge);
        a.appendChild(top);

        a.appendChild(el("h3", "text-lg font-semibold text-ink-100 group-hover:text-accent", m.title));
        a.appendChild(el("p", "text-sm text-ink-400", m.blurb));

        var foot = el("div", "mt-auto flex items-center gap-3 pt-2");
        var track = el("div", "bar-track flex-1");
        var fill = el("div", "bar-fill");
        fill.style.width = (m.exercises ? (solved / m.exercises) * 100 : 0) + "%";
        if (complete) fill.style.background = "var(--color-good)";
        track.appendChild(fill);
        foot.appendChild(track);
        foot.appendChild(el("span", "font-mono text-xs text-ink-400", solved + "/" + m.exercises));
        a.appendChild(foot);
        grid.appendChild(a);
      });

      var s = courseStats();
      $$("[data-course-bar]").forEach(function (n) { n.style.width = (s.doneEx / s.totalEx) * 100 + "%"; });
      $$("[data-course-stat]").forEach(function (n) {
        n.textContent = s.doneLessons + " of " + s.totalLessons + " lessons complete · " +
          s.doneEx + "/" + s.totalEx + " exercises solved";
      });

      var resume = $("[data-resume]");
      if (resume) {
        var target = LESSONS.find(function (m) { return !lessonComplete(m); }) || LESSONS[0];
        resume.href = "lessons/" + target.file;
        resume.textContent = (lessonState(target.id).visited ? "Resume: " : "Start: ") + target.num + ". " + target.title;
      }
    }

    render();

    var reset = $("[data-reset]");
    if (reset) reset.addEventListener("click", function () {
      if (confirm("Erase all saved progress on this device?")) { Progress.reset(); render(); }
    });

    var exp = $("[data-export]");
    if (exp) exp.addEventListener("click", function () {
      var blob = new Blob([Progress.export()], { type: "application/json" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url; a.download = "llm-course-progress.json"; a.click();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    });

    var imp = $("[data-import]");
    if (imp) imp.addEventListener("change", function (e) {
      var f = e.target.files[0];
      if (!f) return;
      var r = new FileReader();
      r.onload = function () {
        try { Progress.import(r.result); render(); }
        catch (err) { alert("Could not read that file."); }
      };
      r.readAsText(f);
    });
  }


  /* ---------- theme ---------- */
  /*
    Three states: "light", "dark", or "system" (no attribute, follows the OS).
    Applied before paint by an inline script in each page's <head>; this block
    only handles the toggle and keeps the button label in sync.
  */

  var THEME_KEY = "llm-course-theme";

  var Theme = {
    stored: function () {
      try { return localStorage.getItem(THEME_KEY) || "system"; } catch (e) { return "system"; }
    },
    effective: function () {
      var s = Theme.stored();
      if (s !== "system") return s;
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    },
    set: function (mode) {
      try {
        if (mode === "system") localStorage.removeItem(THEME_KEY);
        else localStorage.setItem(THEME_KEY, mode);
      } catch (e) {}
      if (mode === "system") document.documentElement.removeAttribute("data-theme");
      else document.documentElement.setAttribute("data-theme", mode);
    },
    cycle: function () {
      var order = ["system", "light", "dark"];
      var next = order[(order.indexOf(Theme.stored()) + 1) % order.length];
      Theme.set(next);
      return next;
    }
  };

  function initTheme() {
    var btn = $("[data-theme-toggle]");
    if (!btn) return;
    var ICON = { system: "◐", light: "☀", dark: "☾" };
    function paint() {
      var s = Theme.stored();
      btn.innerHTML = '<span aria-hidden="true">' + ICON[s] + "</span>";
      btn.title = "Theme: " + s + " (click to change)";
      btn.setAttribute("aria-label", "Theme: " + s);
    }
    btn.addEventListener("click", function () {
      Theme.cycle();
      paint();
      // The interactive diagrams read their colours once, at draw time.
      // Reloading is the simplest way to get them all repainted correctly.
      location.reload();
    });
    paint();
    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: light)");
      var onChange = function () { if (Theme.stored() === "system") location.reload(); };
      if (mq.addEventListener) mq.addEventListener("change", onChange);
      else if (mq.addListener) mq.addListener(onChange);
    }
  }

  /* ---------- viz helpers shared by lesson scripts ---------- */

  var Viz;
  Viz = {
    softmax: function (xs, temp) {
      var t = temp == null ? 1 : Math.max(temp, 1e-6);
      var m = Math.max.apply(null, xs);
      var e = xs.map(function (x) { return Math.exp((x - m) / t); });
      var s = e.reduce(function (a, b) { return a + b; }, 0);
      return e.map(function (v) { return v / s; });
    },
    dot: function (a, b) {
      var s = 0; for (var i = 0; i < a.length; i++) s += a[i] * b[i]; return s;
    },
    norm: function (a) { return Math.sqrt(Viz.dot(a, a)); },
    cosine: function (a, b) {
      var d = Viz.norm(a) * Viz.norm(b);
      return d === 0 ? 0 : Viz.dot(a, b) / d;
    },
    heat: function (v) {
      // v in [0,1]. Dark theme: near-black to bright blue. Light theme: paper to deep blue.
      var t = Math.max(0, Math.min(1, v));
      var s = Viz.light
        ? [246, 247, 251, 29, 78, 216]
        : [12, 20, 45, 134, 170, 255];
      var r = Math.round(s[0] + t * (s[3] - s[0]));
      var g = Math.round(s[1] + t * (s[4] - s[1]));
      var b = Math.round(s[2] + t * (s[5] - s[2]));
      return "rgb(" + r + "," + g + "," + b + ")";
    },
    fmt: function (x, d) { return Number(x).toFixed(d == null ? 2 : d); },
    /* Colours the SVG diagrams draw with. Read from the compiled CSS variables
       so a theme switch needs no changes in the individual lesson scripts. */
    C: {},
    light: false,
    el: el, $: $, $$: $$
  };

  function readPalette() {
    var cs = getComputedStyle(document.documentElement);
    function v(name, fallback) {
      var x = cs.getPropertyValue(name);
      return (x && x.trim()) || fallback;
    }
    var C = Viz.C;
    C.grid = v("--color-ink-700", "#223052");
    C.line = v("--color-ink-600", "#35476f");
    C.muted = v("--color-ink-400", "#8ea0c4");
    C.text = v("--color-ink-100", "#e8eefb");
    C.accent = v("--color-accent", "#6ea8fe");
    C.warm = v("--color-warm", "#ffb454");
    C.good = v("--color-good", "#52d1a4");
    C.bad = v("--color-bad", "#ff7b72");
    C["void"] = v("--color-viz-void", "#0b0f1a");
    Viz.light = document.documentElement.getAttribute("data-theme") === "light" ||
      (!document.documentElement.getAttribute("data-theme") &&
        window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches);
  }
  readPalette();

  window.LC = { Progress: Progress, Viz: Viz, $: $, $$: $$, el: el, stats: courseStats };

  document.addEventListener("DOMContentLoaded", function () {
    readPalette();
    initTheme();
    initLesson();
    initIndex();
  });
})();
