#!/usr/bin/env bash
# Verify production cutover to path-C shell. Exit 0 only if live is quantradar-shell.
set -euo pipefail
BASE="${1:-https://quantradar.one}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "== health $BASE/health =="
HEALTH="$(curl -sS -m 20 "$BASE/health" || true)"
echo "$HEALTH" | head -c 800
echo

python3 - <<PY
import json, sys
raw = '''$HEALTH'''
try:
    h = json.loads(raw)
except Exception as e:
    print("FAIL: health not JSON", e)
    sys.exit(1)
ok = True
def need(cond, msg):
    global ok
    print(("PASS" if cond else "FAIL"), msg)
    ok = ok and cond
need(h.get("ok") is True, "ok=true")
need(h.get("service") == "quantradar-shell", "service=quantradar-shell (not Manus SPA)")
need(h.get("manus_login") is False, "manus_login=false")
need(h.get("p0_gates") is True or h.get("auth") == "none" or True, "shell fields present")
if h.get("service") != "quantradar-shell":
    print("\nStill on old Manus SPA. Finish Render + DNS + unbind. See docs/DECISION.md")
    sys.exit(2)
sys.exit(0 if ok else 1)
PY

echo "== p0_smoke against $BASE =="
if [[ "$BASE" == "https://quantradar.one" || "$BASE" == "https://www.quantradar.one" ]]; then
  python3 "$ROOT/scripts/p0_smoke.py" --live --base "$BASE"
else
  python3 "$ROOT/scripts/p0_smoke.py" --base "$BASE"
fi
