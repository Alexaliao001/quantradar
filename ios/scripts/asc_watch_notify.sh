#!/bin/zsh
set -euo pipefail
ROOT="/Users/rongjianliao/quantradar"
PY="$ROOT/.tools/asc-venv/bin/python"
SCRIPT="$ROOT/ios/scripts/asc_watch.py"
LOG="$HOME/Library/Logs/quantradar-asc-watch.log"
mkdir -p "$(dirname "$LOG")" "$ROOT/ios/build"

{
  echo "---- $(date -u +%Y-%m-%dT%H:%M:%SZ) ----"
  "$PY" "$SCRIPT"
} >>"$LOG" 2>&1 || true

ACTION="wait"
if [[ -f "$ROOT/ios/build/asc_watch_latest.json" ]]; then
  ACTION="$("$PY" -c 'import json,pathlib; p=pathlib.Path("/Users/rongjianliao/quantradar/ios/build/asc_watch_latest.json"); print(json.loads(p.read_text()).get("action","wait"))')"
fi

if [[ "$ACTION" != "wait" ]]; then
  /usr/bin/osascript -e "display notification \"App Store status: $ACTION. Open Cursor to finish.\" with title \"QuantRadar iOS\" sound name \"Glass\""
fi
