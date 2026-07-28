#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
export BROCCOLI_DIR="$B"
R="$B/rish.sh"
ACT="${GROK_ACTIVITY:-ai.x.grok/.main.GrokActivity}"
LOG="$B/window_guard.log"
log(){ echo "[$(date -Iseconds)] goto: $*" >>"$LOG"; }
ok(){ python3 "$B/screen_state.py" 2>/dev/null | python3 -c "import json,sys;exit(0 if json.load(sys.stdin).get('can_inject') else 1)"; }

for t in 1 2 3; do
  bash "$B/ui_pull.sh" || true
  python3 "$B/screen_state.py" >"$B/screen_state.json" 2>/dev/null || true
  ok && { log "OK try $t"; cat "$B/screen_state.json"; exit 0; }
  SCR=$(python3 -c "import json;print(json.load(open('$B/screen_state.json')).get('screen','?'))" 2>/dev/null || echo "?")
  log "try $t screen=$SCR"
  case "$SCR" in
    not_grok_ui|no_ui_dump|unknown)
      "$R" -c "am start --activity-single-top -n $ACT" >/dev/null 2>&1 || true; sleep 1.2 ;;
    grok_login|grok_other)
      "$R" -c "input keyevent 4" >/dev/null 2>&1; sleep 0.3
      "$R" -c "am start --activity-single-top -n $ACT" >/dev/null 2>&1; sleep 1.0 ;;
    grok_voice_or_empty_bar)
      read -r TX TY < <(python3 -c "import json;d=json.load(open('$B/screen_state.json'));xy=d.get('input_xy')or[540,2139];print(xy[0],xy[1])")
      "$R" -c "input tap ${TX:-540} ${TY:-2139}" >/dev/null 2>&1; sleep 0.5 ;;
    *) "$R" -c "am start --activity-single-top -n $ACT" >/dev/null 2>&1; sleep 1.0 ;;
  esac
done
bash "$B/ui_pull.sh" || true
python3 "$B/screen_state.py" >"$B/screen_state.json"
ok || { log "FAIL"; exit 2; }
exit 0
