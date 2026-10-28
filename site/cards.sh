#!/usr/bin/env bash
# Link-preview images: web/og/<name>.png at 1200x630, one per case plus the front page.
# Screenshots each page in ?card=1 mode with headless Chrome. Needs a running preview server:
#   python3 site/build.py --serve &      then      heavy bash site/cards.sh
# Commit the PNGs; the Vercel build only copies them.
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
BASE="${BASE:-http://localhost:8765}"
mkdir -p web/og
shot() { "$CHROME" --headless=new --hide-scrollbars --window-size=1200,630 --virtual-time-budget=8000 --use-angle=swiftshader --enable-unsafe-swiftshader \
  --screenshot="web/og/$1.png" "$BASE$2" 2>/dev/null; echo "web/og/$1.png"; }
shot home "/?card=1&theme=light"
for f in web/data/cases/OS-*.json; do id=$(basename "$f" .json); shot "$id" "/case/$id?card=1&theme=light"; done
