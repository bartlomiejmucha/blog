# -*- coding: utf-8 -*-
"""Code listings for the lessons.

Every listing that shows the companion package is cut out of the real source
files in ../code, so the lessons always show code that compiles and was tested.
Highlighting happens here at build time; the page needs no JavaScript for it.
"""
import html, os, re

CODE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "code")

SWIFT_KEYWORDS = set("""
actor any as associatedtype async await break case catch class continue convenience default defer
deinit do else enum extension fallthrough false fileprivate final for func get guard if import in
indirect init inout internal is lazy let mutating nil nonisolated open operator override private
protocol public repeat required rethrows return self Self set some static struct subscript super
switch throw throws true try typealias unowned var weak where while package consuming
""".split())

TOKEN = re.compile(r'''
    (?P<com>//[^\n]*|/\*.*?\*/)
  | (?P<str>"""(?:.|\n)*?"""|"(?:\\.|[^"\\\n])*")
  | (?P<attr>@[A-Za-z_]\w*|\#[A-Za-z_]\w*)
  | (?P<plain>\$\d+)
  | (?P<num>\b(?:0x[0-9a-fA-F_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)\b)
  | (?P<word>\b[A-Za-z_]\w*\b)
''', re.X | re.S)


def highlight_swift(src):
    out, pos = [], 0
    for m in TOKEN.finditer(src):
        out.append(html.escape(src[pos:m.start()]))
        text = html.escape(m.group(0))
        kind = m.lastgroup
        if kind == "plain":
            kind = None
        elif kind == "word":
            w = m.group(0)
            if w in SWIFT_KEYWORDS:
                kind = "kw"
            elif w[0].isupper():
                kind = "type"
            else:
                kind = None
        out.append('<span class="tk-%s">%s</span>' % (kind, text) if kind else text)
        pos = m.end()
    out.append(html.escape(src[pos:]))
    return "".join(out)


def highlight_shell(src):
    lines = []
    for line in src.split("\n"):
        if line.lstrip().startswith("#"):
            lines.append('<span class="tk-com">%s</span>' % html.escape(line))
        else:
            lines.append(html.escape(line))
    return "\n".join(lines)


def block(src, lang="swift", title=None):
    """A highlighted listing. `title` is shown above it, usually the file path."""
    src = src.strip("\n")
    body = {"swift": highlight_swift, "shell": highlight_shell}.get(lang, html.escape)(src)
    head = '<div class="code-title"><span>%s</span><span>%s</span></div>' % (html.escape(title), lang) if title else ""
    return '<div class="code-block">%s<pre><code>%s</code></pre></div>' % (head, body)


def read(path):
    with open(os.path.join(CODE, path), encoding="utf-8") as f:
        return f.read()


def dedent(lines):
    indent = min((len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0)
    return [l[indent:] for l in lines]


def extract(path, start, end=None, include_end=True):
    """Lines of `path` from the first line containing `start`.

    Without `end`, the snippet runs to the brace that closes the declaration
    that starts there (braces are counted, so `start` should name a func,
    class, struct or extension line). With `end`, it runs to the first later
    line containing `end`. Raises if a marker is missing, so a renamed symbol
    breaks the build instead of silently showing stale code.
    """
    lines = read(path).split("\n")
    try:
        i = next(n for n, l in enumerate(lines) if start in l)
    except StopIteration:
        raise SystemExit("codeblocks: %r not found in %s" % (start, path))
    # Include doc comments directly above the declaration.
    while i > 0 and lines[i - 1].strip().startswith("///"):
        i -= 1
    if end is not None:
        try:
            j = next(n for n in range(i + 1, len(lines)) if end in lines[n])
        except StopIteration:
            raise SystemExit("codeblocks: end %r not found in %s" % (end, path))
        return "\n".join(dedent(lines[i:j + 1] if include_end else lines[i:j]))
    depth, seen = 0, False
    for j in range(i, len(lines)):
        stripped = re.sub(r'"(?:\\.|[^"\\])*"', '""', lines[j].split("//")[0])
        depth += stripped.count("{") - stripped.count("}")
        seen = seen or "{" in stripped
        if seen and depth <= 0:
            return "\n".join(dedent(lines[i:j + 1]))
    raise SystemExit("codeblocks: unbalanced braces after %r in %s" % (start, path))


def source(path, start=None, end=None, title=None, include_end=True):
    """A listing cut from the companion package."""
    text = read(path) if start is None else extract(path, start, end, include_end)
    return block(text, "swift", title or ("code/" + path))
