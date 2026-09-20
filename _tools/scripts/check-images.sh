#!/bin/bash
# Checks markdown images in _posts and _includes before they get committed.
#
#   1. every image carries a kramdown IAL with loading, width and height
#      -> width/height reserve the aspect ratio and keep CLS at zero
#   2. an image that is the first content element of a post must be
#      loading="eager" -> it is the LCP element there, lazy delays it
#   3. every image path resolves to a file in this repo
#
# Install as a git hook:  ln -sf ../../_tools/scripts/check-images.sh .git/hooks/pre-commit
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

fail=0
report() { echo "  $1:$2: $3"; fail=1; }

files=$(git diff --cached --name-only --diff-filter=ACM -- '_posts/*.md' '_includes/*.md')
[ -n "$files" ] || files=$(ls _posts/*.md _includes/*.md 2>/dev/null)

for f in $files; do
  [ -f "$f" ] || continue

  # line number of the first content line after the front matter
  first_content=$(awk 'NR==1 && $0=="---" {fm=1; next}
                       fm==1 && $0=="---" {fm=2; next}
                       fm==2 && NF {print NR; exit}' "$f")

  while IFS=: read -r lineno line; do
    [ -n "$lineno" ] || continue

    path=$(printf '%s' "$line" | sed -n 's/.*!\[[^]]*\](\([^)]*\)).*/\1/p')
    ial=$(printf '%s' "$line" | sed -n 's/.*!\[[^]]*\]([^)]*){\([^}]*\)}.*/\1/p')

    if [ -z "$ial" ]; then
      report "$f" "$lineno" "image has no attribute list — needs {: loading=\"lazy\" width=\"W\" height=\"H\"}"
      continue
    fi
    case "$ial" in *width=*) ;; *) report "$f" "$lineno" "image is missing width" ;; esac
    case "$ial" in *height=*) ;; *) report "$f" "$lineno" "image is missing height" ;; esac
    case "$ial" in *loading=*) ;; *) report "$f" "$lineno" "image is missing loading" ;; esac

    if [ "$lineno" = "${first_content:-}" ] && ! printf '%s' "$ial" | grep -q 'loading="eager"'; then
      report "$f" "$lineno" "first content element must be loading=\"eager\" — it is the LCP element"
    fi

    if [ -n "$path" ] && [ ! -f ".$path" ]; then
      report "$f" "$lineno" "image path does not resolve: $path"
    fi
  done < <(grep -n '!\[[^]]*\](' "$f")
done

if [ "$fail" -ne 0 ]; then
  echo
  echo "check-images: commit blocked. Fix the images above, or bypass with --no-verify."
  exit 1
fi
exit 0
