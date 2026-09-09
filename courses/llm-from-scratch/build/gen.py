#!/usr/bin/env python3
"""Generates the static course: index.html, lessons/NN-*.html, assets/js/course.js."""
import json, os, re, sys, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "build"))

from content_part1 import LESSONS as L1
from content_part2 import LESSONS as L2
from content_part3 import LESSONS as L3
from content_part4 import LESSONS as L4

LESSONS = L1 + L2 + L3 + L4

# ---------------------------------------------------------------- helpers

def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s

for i, L in enumerate(LESSONS, start=1):
    L["num"] = i
    L["id"] = "l%02d" % i
    L["file"] = "%02d-%s.html" % (i, slug(L["title"]))

def ex_block(e, idx):
    """Render one exercise from a dict."""
    t = e["type"]
    attrs = ['data-ex', 'data-ex-id="%d"' % idx, 'data-ex-type="%s"' % t]
    if t in ("mcq", "multi"):
        answer = e["answer"] if isinstance(e["answer"], str) else ",".join(str(x) for x in e["answer"])
        attrs.append('data-answer="%s"' % answer)
    elif t == "numeric":
        attrs.append('data-answer="%s"' % e["answer"])
        attrs.append('data-tolerance="%s"' % e.get("tolerance", 0.001))
        if e.get("placeholder"): attrs.append('data-placeholder="%s"' % e["placeholder"])
    elif t == "fill":
        attrs.append('data-answer="%s"' % "|".join(e["answer"]))
        if e.get("placeholder"): attrs.append('data-placeholder="%s"' % e["placeholder"])

    parts = ['<div class="card-tight space-y-3" %s>' % " ".join(attrs)]
    parts.append('<div class="flex items-center gap-2">'
                 '<span class="pill font-mono">Exercise %d</span>'
                 '<span class="text-xs uppercase tracking-wider text-ink-600">%s</span></div>'
                 % (idx, {"mcq": "one answer", "multi": "select all that apply",
                          "numeric": "compute it", "fill": "type the term",
                          "order": "put in order"}[t]))
    parts.append('<div class="prose-block text-sm" data-ex-prompt>%s</div>' % e["prompt"])

    if t in ("mcq", "multi"):
        parts.append('<div class="space-y-2">')
        for i, opt in enumerate(e["options"]):
            parts.append('<button type="button" data-opt="%d">%s</button>' % (i, opt))
        parts.append('</div>')
    elif t == "order":
        parts.append('<div class="space-y-2" data-ex-order>')
        for i, item in enumerate(e["items"]):
            parts.append('<div data-item="%d"><span>%s</span></div>' % (i, item))
        parts.append('</div>')

    parts.append('<div class="note text-sm" data-ex-explain hidden>%s</div>' % e["explain"])
    parts.append('</div>')
    return "\n".join(parts)

def section_block(s):
    sid = s.get("id") or slug(s["title"])
    out = ['<section class="space-y-4">',
           '<h2 id="%s" class="scroll-mt-24 text-2xl">%s</h2>' % (sid, s["title"]),
           '<div class="prose-block">%s</div>' % s["body"]]
    if s.get("figure"):
        out.append(s["figure"])
    out.append('</section>')
    return "\n".join(out)

HEAD = """<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}assets/css/site.css">
<script>
/* Applied before first paint so switching themes never flashes the old one. */
(function () {{
  try {{
    var t = localStorage.getItem("llm-course-theme");
    if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t);
  }} catch (e) {{}}
}})();
</script>
<script src="{base}assets/js/course.js" defer></script>
<script src="{base}assets/js/app.js" defer></script>"""

def lesson_page(L, prev, nxt):
    goals = "\n".join('<li>%s</li>' % g for g in L["goals"])
    sections = "\n\n".join(section_block(s) for s in L["sections"])
    exercises = "\n".join(ex_block(e, i + 1) for i, e in enumerate(L["exercises"]))
    viz = ('<script src="../assets/js/viz/%s.js" defer></script>' % L["id"]) if L.get("viz") else ""
    for data in L.get("viz_data", []):
        viz = ('<script src="../assets/js/viz/%s.js" defer></script>' % data) + viz


    prev_html = ('<a class="btn" href="%s" data-nav-prev>← %d. %s</a>' % (prev["file"], prev["num"], prev["title"])
                 if prev else '<a class="btn" href="../index.html" data-nav-prev>← Course home</a>')
    next_html = ('<a class="btn btn-primary" href="%s" data-nav-next>%d. %s →</a>' % (nxt["file"], nxt["num"], nxt["title"])
                 if nxt else '<a class="btn btn-primary" href="../index.html" data-nav-next>Finish → Course home</a>')

    recap = ""
    if L.get("recap"):
        recap = ('<div class="note note-key"><p class="font-semibold text-ink-100 mb-2">Lesson in one breath</p>'
                 '<p class="text-sm">%s</p></div>' % L["recap"])

    return """<!doctype html>
<html lang="en">
<head>
{head}
</head>
<body data-lesson="{id}" class="min-h-screen">
<header class="sticky top-0 z-30 border-b border-ink-800 bg-ink-950/85 backdrop-blur">
  <div class="wrap-wide flex items-center gap-4 py-3">
    <a href="../index.html" class="btn btn-ghost btn-sm">← Course</a>
    <div class="hidden flex-1 sm:block">
      <div class="bar-track"><div class="bar-fill" data-course-bar style="width:0%"></div></div>
    </div>
    <span class="hidden font-mono text-xs text-ink-400 md:inline" data-course-stat></span>
    <button class="btn btn-sm btn-ghost" data-theme-toggle type="button" title="Theme"></button>
    <span class="pill font-mono">Lesson {num} / {total}</span>
  </div>
</header>

<div class="wrap-wide grid gap-8 py-10 lg:grid-cols-[minmax(0,1fr)_14rem]">
  <main class="min-w-0 space-y-10">
    <div class="space-y-4">
      <span class="pill">{part}</span>
      <h1 class="text-4xl leading-tight">{num}. {title}</h1>
      <p class="lead">{blurb}</p>
      <div class="card">
        <p class="mb-2 text-sm font-semibold text-ink-100">By the end of this lesson you can</p>
        <ul class="prose-block list-disc space-y-1 pl-6 text-sm">{goals}</ul>
      </div>
    </div>

{sections}

    {recap}

    <section class="space-y-4">
      <div class="flex items-center justify-between gap-4">
        <h2 id="exercises" class="scroll-mt-24 text-2xl">Practice</h2>
        <div class="flex items-center gap-3">
          <div class="bar-track w-28"><div class="bar-fill" data-lesson-ex-bar style="width:0%"></div></div>
          <span class="font-mono text-xs text-ink-400" data-lesson-ex-count></span>
        </div>
      </div>
      <p class="text-sm text-ink-400">Answers are checked in your browser and saved to this device. Get one wrong and you can retry as many times as you like.</p>
{exercises}
    </section>

    <div class="card flex flex-wrap items-center justify-between gap-4">
      <div>
        <p class="text-sm font-semibold text-ink-100">Done with this lesson?</p>
        <p class="text-xs text-ink-400">A lesson counts as complete once it is marked read and every exercise is solved.</p>
      </div>
      <button class="btn" data-mark-read>Mark lesson as read</button>
    </div>

    <nav class="flex flex-wrap items-center justify-between gap-3 border-t border-ink-800 pt-6">
      {prev}
      {next}
    </nav>
    <p class="text-center text-xs text-ink-600">Tip: press <span class="kbd">←</span> and <span class="kbd">→</span> to move between lessons.</p>
  </main>

  <aside class="hidden lg:block">
    <div class="sticky top-20 space-y-2">
      <p class="px-2 text-xs font-semibold uppercase tracking-widest text-ink-600">On this page</p>
      <nav data-toc class="space-y-0.5"></nav>
    </div>
  </aside>
</div>
{viz}
</body>
</html>""".format(
        head=HEAD.format(title="%d. %s — LLMs from scratch" % (L["num"], L["title"]), base="../"),
        id=L["id"], num=L["num"], total=len(LESSONS), part=L["part"], title=L["title"],
        blurb=L["blurb"], goals=goals, sections=sections, recap=recap, exercises=exercises,
        prev=prev_html, next=next_html, viz=viz)

INDEX = """<!doctype html>
<html lang="en">
<head>
{head}
</head>
<body class="min-h-screen">
<header class="border-b border-ink-800">
  <div class="wrap-wide flex items-center justify-between py-4">
    <span class="font-mono text-sm text-ink-300">LLMs, from first principles</span>
    <div class="flex items-center gap-3">
      <button class="btn btn-sm btn-ghost" data-theme-toggle type="button" title="Theme"></button>
      <span class="pill font-mono">{total} lessons</span>
    </div>
  </div>
</header>

<main class="wrap-wide space-y-10 py-12">
  <section class="space-y-5">
    <h1 class="text-5xl leading-tight">How large language models actually work</h1>
    <p class="lead max-w-2xl">A slow, visual, hands-on course. It starts with "what is a token" and ends with mixture-of-experts routing, speculative decoding, and RLHF. Every lesson has interactive diagrams you can poke at and exercises that check your answer.</p>
    <div class="flex flex-wrap items-center gap-3">
      <a class="btn btn-primary" data-resume href="lessons/{first}">Start the course</a>
      <a class="btn" href="#map">See the full map</a>
    </div>
    <div class="card space-y-3">
      <div class="flex items-center justify-between text-sm">
        <span class="font-semibold text-ink-100">Your progress</span>
        <span class="font-mono text-xs text-ink-400" data-course-stat></span>
      </div>
      <div class="bar-track"><div class="bar-fill" data-course-bar style="width:0%"></div></div>
      <div class="flex flex-wrap items-center gap-2 pt-1">
        <button class="btn btn-sm" data-export>Export progress</button>
        <label class="btn btn-sm cursor-pointer">Import<input type="file" accept="application/json" class="hidden" data-import></label>
        <button class="btn btn-sm" data-reset>Reset</button>
        <span class="text-xs text-ink-600">Saved in this browser's local storage.</span>
      </div>
    </div>
  </section>

  <section id="map" class="scroll-mt-8 space-y-4">
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" data-lesson-grid></div>
  </section>

  <section class="card space-y-3">
    <h2 class="text-xl">How to use this course</h2>
    <div class="prose-block text-sm">
      <ul>
        <li>Go in order. Each lesson assumes the previous one.</li>
        <li>Play with every diagram before reading past it. Move the sliders, break things, watch what changes.</li>
        <li>Do the exercises with the text hidden if you can. Retry as often as you like.</li>
        <li>Mark a lesson read when you finish it. Progress lives in local storage on this device, so use Export if you want to move it.</li>
        <li>The ◐ button in the header cycles the theme: follow your system, force light, force dark.</li>
      </ul>
    </div>
  </section>
</main>
<footer class="border-t border-ink-800 py-8 text-center text-xs text-ink-600">Built as a static site. No tracking, no network calls, everything runs in your browser.</footer>
</body>
</html>"""

def main():
    course = {"lessons": [{"id": L["id"], "num": L["num"], "title": L["title"], "file": L["file"],
                           "part": L["part"], "blurb": L["blurb"], "exercises": len(L["exercises"])}
                          for L in LESSONS]}
    with open(os.path.join(ROOT, "assets/js/course.js"), "w") as f:
        f.write("window.COURSE = " + json.dumps(course, indent=2) + ";\n")

    for i, L in enumerate(LESSONS):
        prev = LESSONS[i - 1] if i > 0 else None
        nxt = LESSONS[i + 1] if i < len(LESSONS) - 1 else None
        with open(os.path.join(ROOT, "lessons", L["file"]), "w") as f:
            f.write(lesson_page(L, prev, nxt))

    with open(os.path.join(ROOT, "index.html"), "w") as f:
        f.write(INDEX.format(head=HEAD.format(title="LLMs from scratch — a visual course", base=""),
                             total=len(LESSONS), first=LESSONS[0]["file"]))
    print("generated %d lessons" % len(LESSONS))

if __name__ == "__main__":
    main()
