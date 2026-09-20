#!/bin/sh
# Regenerates lesson pages, then compiles Tailwind locally.
#
# Needs the standalone Tailwind CLI (no Node required):
#   https://github.com/tailwindlabs/tailwindcss/releases  ->  tailwindcss-macos-arm64
# Put it on your PATH as `tailwindcss`, or set TAILWIND_BIN.
set -e
cd "$(dirname "$0")"

BIN="${TAILWIND_BIN:-tailwindcss}"
if ! command -v "$BIN" >/dev/null 2>&1; then
	if [ -x ./tools/tailwindcss ]; then
		BIN=./tools/tailwindcss
	else
		echo "tailwindcss CLI not found. Set TAILWIND_BIN or install the standalone binary." >&2
		exit 1
	fi
fi

python3 build/gen.py
"$BIN" -i src/input.css -o assets/css/site.css --minify
echo "built → open index.html"
