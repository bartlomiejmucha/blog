#!/bin/bash
# Local preview of the blog. `remote_theme` only resolves on GitHub Pages, so this
# stitches the content branch (blog@pages) and the theme branch (blog@theme) into
# one Jekyll source directory (.preview) and serves it on http://127.0.0.1:4000
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
P="$ROOT/blog@pages"
T="$ROOT/blog@theme"
S="$ROOT/.preview"
export PATH="$HOME/.gem/ruby/2.6.0/bin:$PATH"

pkill -f "jekyll serve" 2>/dev/null || true
rm -rf "$S"; mkdir -p "$S/_includes" "$S/assets"

# content branch
for f in "$P"/*.md "$P"/_posts "$P"/tags "$P"/sitemap.xml "$P"/robots.txt "$P"/CNAME; do
  [ -e "$f" ] && ln -sfn "$f" "$S/$(basename "$f")"
done
# assets/images exists in both branches and remote_theme merges them per file,
# so the preview has to do the same rather than link one directory over the other.
# The content branch is listed second, matching Jekyll: site files win over theme files.
mkdir -p "$S/assets/images"
for f in "$T"/assets/images/* "$P"/assets/images/*; do
  [ -e "$f" ] && ln -sfn "$f" "$S/assets/images/$(basename "$f")"
done
ln -sfn "$P/_includes/about-me.md" "$S/_includes/about-me.md"

# theme branch
ln -sfn "$T/_layouts" "$S/_layouts"
ln -sfn "$T/_sass"    "$S/_sass"
ln -sfn "$T/assets/css" "$S/assets/css"
ln -sfn "$T/assets/js"  "$S/assets/js"
for f in "$T"/_includes/*.html; do ln -sfn "$f" "$S/_includes/$(basename "$f")"; done
for f in "$T"/assets/*.json "$T"/assets/*.xml; do
  [ -e "$f" ] && ln -sfn "$f" "$S/assets/$(basename "$f")"
done

# remote_theme cannot resolve locally
sed '/remote_theme/d; /jekyll-remote-theme/d' "$P/_config.yml" > "$S/_config.yml"

cd "$S"
exec jekyll serve --watch --port 4000 --host 127.0.0.1
