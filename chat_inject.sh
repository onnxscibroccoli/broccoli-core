#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
OUTBOX="$B/outbox_context.txt"
R="$B/rish.sh"
LOG="$B/inject.log"
log(){ echo "[$(date -Iseconds)] $*" >>"$LOG"; }
[ -f "$OUTBOX" ] || { log "ERR no outbox"; exit 1; }
[ "$(wc -c <"$OUTBOX" | tr -d ' ')" -gt 0 ] || { log "ERR empty"; exit 1; }
log "goto"
bash "$B/go_to_grok_chat.sh" >>"$LOG" 2>&1 || { log "ERR window"; exit 2; }
head -c 6000 "$OUTBOX" > "$B/.clip_payload.txt"
"$B/clipboard.sh" set "$B/.clip_payload.txt" || { log "ERR clip"; exit 1; }
log "clip ok"
STATE=$(cat "$B/screen_state.json")
read -r IX IY < <(echo "$STATE" | python3 -c "import json,sys;d=json.load(sys.stdin);xy=d.get('input_xy')or[540,2139];print(xy[0],xy[1])")
"$R" -c "input tap $IX $IY"; sleep 0.4
"$R" -c "input tap $IX $IY"; sleep 0.35
"$R" -c "input keyevent 279"; sleep 0.9
bash "$B/ui_pull.sh" >>"$LOG" 2>&1 || true
python3 "$B/screen_state.py" >"$B/screen_state.json"
read -r SX SY < <(python3 -c "
import json;d=json.load(open('$B/screen_state.json'))
xy=d.get('send_xy')
if xy: print(xy[0],xy[1])
else:
 p=json.load(open('$B/chat_profile.json')).get('inject',{}) if __import__('pathlib').Path('$B/chat_profile.json').is_file() else {}
 print(p.get('CHAT_SEND_X',1001),p.get('CHAT_SEND_Y',2203))
")
log "send $SX $SY"
"$R" -c "input tap $SX $SY"
log "done"; exit 0
