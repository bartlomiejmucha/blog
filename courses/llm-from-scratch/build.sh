#!/bin/sh
# Regenerates lesson pages, then compiles Tailwind locally.
set -e
cd "$(dirname "$0")"
python3 build/gen.py
./tools/tailwindcss -i src/input.css -o assets/css/site.css --minify
echo "built → open index.html"
