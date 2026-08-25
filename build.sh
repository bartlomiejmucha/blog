#!/usr/bin/env bash
# Regenerates styles.css from index.html. Edit custom.css by hand; never edit styles.css.
#
#   ./build.sh          one-off build
#   ./build.sh --watch  rebuild on change
#
# Needs the standalone Tailwind CLI (no Node required):
#   https://github.com/tailwindlabs/tailwindcss/releases  ->  tailwindcss-macos-arm64
# Put it on your PATH as `tailwindcss`, or set TAILWIND_BIN.

set -euo pipefail
cd "$(dirname "$0")"

BIN="${TAILWIND_BIN:-tailwindcss}"
if ! command -v "$BIN" >/dev/null 2>&1; then
	# Fall back to the sibling-checkout copy used by the local Blog workspace.
	if [ -x ../.tools/tailwindcss ]; then
		BIN=../.tools/tailwindcss
	else
		echo "tailwindcss CLI not found. Set TAILWIND_BIN or install the standalone binary." >&2
		exit 1
	fi
fi

"$BIN" -c tailwind.config.js -i src/input.css -o styles.css --minify "$@"
