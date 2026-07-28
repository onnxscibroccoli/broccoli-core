#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
export BROCCOLI_DIR="$B"
R="$B/rish.sh"
LOG="$B/god_mode_getevent.log"
SEC="${GOD_MODE_SECONDS:-90}"
PRACTICE='god mode learn — paste and send this line'

echo "=============================================="
echo "  GOD MODE: you send ONE message by hand"
echo "  Clipboard has practice text — paste it, then Send"
echo "  (Tab then Enter is fine). We only RECORD."
echo "=============================================="

printf '%s\n' "$PRACTICE" > "$B/god_mode_clip.txt"
"$B/clipboard.sh" set "$B/god_mode_clip.txt"

echo "[1] Opening Grok..."
bash "$B/grok_launch.sh" || exit 2
bash "$B/wait_grok_fg.sh" || exit 2

echo "[2] Practice line is on clipboard:"
echo "    $PRACTICE"
echo "[3] When countdown ends: tap box → PASTE → send how you always do."
for t in 5 4 3 2 1; do echo "    Recording in $t..."; sleep 1; done

: > "$LOG"
"$R" -c "timeout $SEC getevent -lt" >> "$LOG" 2>&1 &
end=$(( $(date +%s) + SEC ))
while [ "$(date +%s)" -lt "$end" ]; do
  sleep 8
  bash "$B/wait_grok_fg.sh" >/dev/null 2>&1 || bash "$B/grok_launch.sh" >/dev/null 2>&1 || true
done
wait 2>/dev/null || true

python3 "$B/parse_learn_log.py" 2>/dev/null || true

# Fallback: you already sent — dump UI and grab Send / composer
bash "$B/ui_grok.sh" 2>/dev/null || true
if [ -f "$B/window_dump.xml" ]; then
  python3 "$B/grok_ui_coords.py" > "$B/post_learn_coords.json" 2>/dev/null || true
  python3 <<'PY'
import json
from pathlib import Path
B = Path(__import__("os").environ["BROCCOLI_DIR"])
learn = json.loads((B/"learned_inject.json").read_text()) if (B/"learned_inject.json").is_file() else {"ok": False, "taps": [], "submit_keys": []}
coords = {}
if (B/"post_learn_coords.json").is_file():
    try: coords = json.loads((B/"post_learn_coords.json").read_text())
    except: pass
send = coords.get("send")
if send and not learn.get("taps"):
    learn["ui_send_fallback"] = send
    learn["ok"] = True
if coords.get("input"):
    learn["ui_input"] = coords["input"]
(B/"learned_inject.json").write_text(json.dumps(learn, indent=2))
prof = json.loads((B/"chat_profile.json").read_text()) if (B/"chat_profile.json").is_file() else {}
inj = prof.setdefault("inject", {})
if coords.get("input"):
    inj["CHAT_INPUT_X"] = coords["input"]["x"]
    inj["CHAT_INPUT_Y"] = coords["input"]["y"]
if send:
    inj["CHAT_SEND_X"] = send["x"]
    inj["CHAT_SEND_Y"] = send["y"]
prof["learned"] = learn
(B/"chat_profile.json").write_text(json.dumps(prof, indent=2))
PY
fi

python3 <<'PY'
import json
from pathlib import Path
B = Path(__import__("os").environ["BROCCOLI_DIR"])
learn = json.loads((B/"learned_inject.json").read_text()) if (B/"learned_inject.json").is_file() else {}
ok = bool(learn.get("taps") or learn.get("submit_keys") or learn.get("ui_send_fallback"))
s = json.loads((B/"state.json").read_text()) if (B/"state.json").is_file() else {}
s["god_mode_learned"] = ok
s["phase"] = "god_mode_done"
(B/"state.json").write_text(json.dumps(s, indent=2))
print("god_mode_learned =", ok)
if not ok:
    print("WARN: getevent empty — check:", B/"god_mode_getevent.log")
PY

echo "Learn finished. We did NOT auto-inject."
echo "If you sent the practice line, that counts as success."
