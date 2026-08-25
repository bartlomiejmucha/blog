#!/usr/bin/env bash
# Compile the Tailwind utilities used by the theme into assets/css/tailwind.css.
# Run from the repository root after changing classes in _layouts or _includes.
#
#   ./script/build-css.sh          one-off build
#   ./script/build-css.sh --watch  rebuild on change
#
# Needs the standalone Tailwind CLI (no Node required):
#   https://github.com/tailwindlabs/tailwindcss/releases  ->  tailwindcss-macos-arm64
# Put it on your PATH as `tailwindcss`, or set TAILWIND_BIN.

set -euo pipefail
cd "$(dirname "$0")/.."

BIN="${TAILWIND_BIN:-tailwindcss}"
if ! command -v "$BIN" >/dev/null 2>&1; then
	echo "tailwindcss CLI not found. Set TAILWIND_BIN or install the standalone binary." >&2
	exit 1
fi

"$BIN" --config tailwind.config.js --input _tailwind/input.css --output assets/css/tailwind.css --minify "$@"
