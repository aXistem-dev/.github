#!/bin/bash
# Render the PNG versions of the logo and the avatar from their SVGs with headless Chromium.
#   CHROME=/path/to/chrome-headless-shell scripts/render.sh
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME=${CHROME:-$(command -v chromium || command -v google-chrome)}
shot() { # svg png size background
  local page; page=$(mktemp --suffix=.html)
  echo "<html><body style='margin:0;background:$4'><img src='file://$PWD/$1' width=$3 height=$3 style='display:block'></body></html>" > "$page"
  "$CHROME" --headless --no-sandbox --disable-gpu --hide-scrollbars --default-background-color=00000000 \
    --window-size="$3,$3" --screenshot="$PWD/$2" "file://$page" >/dev/null 2>&1
  rm -f "$page"
}
shot assets/avatar.svg assets/avatar.png 1024 '#0d1117'
shot assets/logo.svg assets/logo.png 1024 transparent
