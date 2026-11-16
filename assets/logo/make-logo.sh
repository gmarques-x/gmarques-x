#!/usr/bin/env bash
# Shoot the Project Grove logo shown beside the Project Grove section of the
# profile README.
#
#   assets/logo/make-logo.sh [--mode paper|night|both] [--out DIR]
#
# Writes, in DIR (default: assets/, the folder above this script):
#   project-grove-logo-paper.png   on Atlas Paper (light readers)
#   project-grove-logo-night.png   on Atlas Night (dark readers)
# each 300 x 300: logo.html, a 150 x 150 page, shot at 2x. The corners are
# rounded and transparent (RGBA), so the page is shot on a transparent
# background. --mode picks one of them; both is the default.
#
# Needs Google Chrome (or GROVE_CHROME, a Chrome binary). Optionally Pillow:
# with it (python3, or GROVE_PYTHON, a Python that has it) the logos are
# reduced to 256 dithered colours by quantize-logo.py, beside this script
# (the soft corners kept); without it they stay full colour.
#
# Follows assets/banner/make-banner.sh of Project Grove.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
chrome="${GROVE_CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
python="${GROVE_PYTHON:-python3}"
out="$(cd "$here/.." && pwd)"
mode=both

usage() { sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) mode="${2:-}"; shift 2 ;;
    --out) out="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done
case "$mode" in paper) modes=paper ;; night) modes=night ;; both) modes="paper night" ;;
  *) echo "--mode is paper, night or both" >&2; exit 2 ;; esac
[ -x "$chrome" ] || { echo "no Chrome at $chrome (set GROVE_CHROME)" >&2; exit 1; }
mkdir -p "$out"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

quantize=0
if "$python" -c "import PIL" 2>/dev/null; then quantize=1; else echo "no Pillow: the logos stay full colour (RGBA)" >&2; fi

for m in $modes; do
  png="$tmp/project-grove-logo-$m.png"
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --virtual-time-budget=3000 --window-size=150,150 --default-background-color=00000000 --screenshot="$png" \
    "file://$here/logo.html#$m" >/dev/null 2>&1
  [ -s "$png" ] || { echo "Chrome wrote nothing for $m" >&2; exit 1; }
  if [ "$quantize" = 1 ]; then
    "$python" -I "$here/quantize-logo.py" "$png" "$out/project-grove-logo-$m.png"
  else
    cp "$png" "$out/project-grove-logo-$m.png"
  fi
  echo "$out/project-grove-logo-$m.png"
done
