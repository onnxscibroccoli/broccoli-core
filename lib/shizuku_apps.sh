#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
BRO="$HOME/broccoli"
CFG="$BRO/lib/app_targets.json"
APP="${1:-${BROCC_CHAT_APP:-grok}}"
ACTION="${2:-launch}"

pick_pkg() {
  python3 - "$APP" "$CFG" <<'PY'
import json, sys
app, cfg = sys.argv[1], sys.argv[2]
d = json.load(open(cfg))
apps = d["apps"]
key = app if app in apps else d.get("default", "grok")
if key not in apps and app in ("gemini", "google"):
    key = "gemini_google" if "gemini_google" in apps else "gemini"
meta = apps.get(key) or apps[d["default"]]
print(meta["package"])
print(meta.get("launch", f'am start -p {meta["package"]}'))
PY
}

bash "$HOME/aim_rish_ensure.sh" >/dev/null 2>&1 || true
mapfile -t _lines < <(pick_pkg)
PKG="${_lines[0]:-ai.x.grok}"
LAUNCH="${_lines[1]:-am start -p $PKG}"

case "$ACTION" in
  launch|foreground)
    rish -c "$LAUNCH" || rish -c "monkey -p $PKG -c android.intent.category.LAUNCHER 1"
    sleep 1.2
    rish -c "am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p $PKG" 2>/dev/null || true
    echo "SHIZUKU_APP ok pkg=$PKG action=$ACTION"
    ;;
  stop)
    rish -c "am force-stop $PKG" && echo "stopped $PKG"
    ;;
  resolve)
    echo "pkg=$PKG"
    rish -c "pm path $PKG" 2>/dev/null || echo "pm path failed (not installed?)"
    ;;
  *)
    echo "usage: shizuku_apps.sh [grok|chatgpt|gemini] launch|foreground|stop|resolve"
    exit 1
    ;;
esac
