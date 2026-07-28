#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
mkdir -p "$B"/{tools,lib,reports,queue,thread,prompts}

# --- idle (older stack) ---
cat > "$B/lib/user_idle_sec.sh" <<'IDLE'
#!/data/data/com.termux/files/usr/bin/bash
# Seconds since last user touch (approx). Termux:am get-touch-events or fallback 99
if [ -f /proc/interrupts ]; then echo 99; exit 0; fi
echo 99
IDLE
chmod +x "$B/lib/user_idle_sec.sh"
# Better if you already had a real implementation — restore from backup:
for bak in "$B/lib/user_idle_sec.sh.bak"* "$B/tools/collab_rish_loop.sh.bak"*; do
  [ -f "$bak" ] && cp -a "$bak" "${bak%.bak*}" 2>/dev/null || true
done 2>/dev/null || true

cat > "$B/lib/disk_gate.sh" <<'DG'
#!/data/data/com.termux/files/usr/bin/bash
MIN_FREE_MB="${MIN_FREE_MB:-80}"
avail_mb(){ df -k "$HOME" 2>/dev/null | awk 'NR==2{printf "%d", $4/1024}'; }
disk_ok(){ [ "$(avail_mb)" -ge "$MIN_FREE_MB" ]; }
DG
chmod +x "$B/lib/disk_gate.sh"

# --- should wire (agenda gate — NOT every poll) ---
cat > "$B/tools/agent_should_wire.sh" <<'SW'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
# 1) explicit task
[ -s "$B/queue/agent_task.txt" ] && exit 0
# 2) pending worker line that looks like wire/agenda
if [ -s "$B/queue/pending.txt" ]; then
  head -1 "$B/queue/pending.txt" | grep -qiE 'wire|grok|prompt|agenda' && exit 0
fi
# 3) sanitized prompt changed since last wire
P="$B/reports/SANITIZED_PROMPT.md"
H="$B/meta/last_wired_prompt.sha"
[ -f "$P" ] || exit 1
CUR="$(sha256sum "$P" 2>/dev/null | awk '{print $1}' || echo)"
OLD="$(cat "$H" 2>/dev/null || echo)"
[ -n "$CUR" ] && [ "$CUR" != "$OLD" ] && exit 0
# 4) new user lines in inbox since last wire
IN="$B/meta/last_wire_ts"
LAST=0; [ -f "$IN" ] && LAST=$(cat "$IN" 2>/dev/null || echo 0)
if [ -s "$B/inbox/chat_lines.txt" ]; then
  MT=$(stat -c %Y "$B/inbox/chat_lines.txt" 2>/dev/null || echo 0)
  [ "$MT" -gt "$LAST" ] && exit 0
fi
exit 1
SW
chmod +x "$B/tools/agent_should_wire.sh"

# --- build sanitized prompt (conversation + task, no vault) ---
cat > "$B/tools/write_sanitized_prompt.sh" <<'WSP'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
OUT="$B/reports/SANITIZED_PROMPT.md"
MAX=3200
TASK=""
[ -s "$B/queue/agent_task.txt" ] && TASK="$(head -c 800 "$B/queue/agent_task.txt")"
ROLL=""
[ -f "$B/thread/rolling_summary.txt" ] && ROLL="$(head -c 600 "$B/thread/rolling_summary.txt")"
CONV=""
[ -f "$B/thread/conversation.jsonl" ] && CONV="$(tail -20 "$B/thread/conversation.jsonl" | head -c 2000)"
[ -f "$B/inbox/chat_lines.txt" ] && CONV="$CONV

$(tail -15 "$B/inbox/chat_lines.txt" | head -c 1200)"
TPL="$(cat "$B/prompts/agent_turn.txt" 2>/dev/null || echo 'Continue Broccoli agenda. Context:
{{CONTEXT}}
Task: {{TASK}}')"
BODY="${TPL//\{\{CONTEXT\}\}/${ROLL}
${CONV}}"
BODY="${BODY//\{\{TASK\}\}/${TASK:-Execute next automation step; reply with one concrete action.}}"
printf '%s' "$BODY" | head -c "$MAX" > "$OUT"
WSP
chmod +x "$B/tools/write_sanitized_prompt.sh"

# --- wire: open Grok, focus field, paste, send (older working pattern) ---
cat > "$B/tools/wire_send_ui.sh" <<'WIRE'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
LOG="$B/reports/wire_send.log"
PROMPT="${1:-}"
[ -n "$PROMPT" ] || PROMPT="$(cat 2>/dev/null || true)"
[ -n "$PROMPT" ] || { echo "wire: empty prompt" >>"$LOG"; exit 1; }

PKG="${GROK_PKG:-com.ai.x.grok}"
AM_MAIN="${GROK_ACTIVITY:-}"

log(){ echo "$(date -Iseconds) $*" >>"$LOG"; }
log "wire start len=${#PROMPT}"

# Open app
if [ -n "$AM_MAIN" ]; then
  am start -n "$PKG/$AM_MAIN" >>"$LOG" 2>&1 || true
else
  monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >>"$LOG" 2>&1 || \
  am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER "$PKG" >>"$LOG" 2>&1 || true
fi
sleep "${WIRE_OPEN_SEC:-2}"

# Dump UI for send button (optional)
bash "$B/lib/ui_dump_rish.sh" >>"$LOG" 2>&1 || true
DUMP="$B/reports/ui_dump.xml"

# Focus composer: tap heuristic (bottom-center) if no rish id
tap_send(){
  python3 <<'PY' 2>>"$LOG" || return 1
import re, subprocess, os
from pathlib import Path
dump = Path(os.environ.get("B","/data/data/com.termux/files/home/broccoli"))/"reports/ui_dump.xml"
xml = dump.read_text(errors="replace") if dump.is_file() else ""
# send button
for pat in [r'content-desc="([^"]*send[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
            r'text="Send"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
            r'resource-id="[^"]*send[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"']:
    m = re.search(pat, xml, re.I)
    if m:
        g = m.groups()
        if len(g)==5:
            x1,y1,x2,y2 = map(int, g[1:5])
        else:
            x1,y1,x2,y2 = map(int, g[0:4])
        x,y = (x1+x2)//2, (y1+y2)//2
        subprocess.run(["input","tap",str(x),str(y)], check=False)
        raise SystemExit(0)
# composer: editable near bottom
for m in re.finditer(r'class="android.widget.EditText"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
    x1,y1,x2,y2 = map(int, m.groups())
    if y1 > 800:
        subprocess.run(["input","tap",str((x1+x2)//2),str((y1+y2)//2)], check=False)
        raise SystemExit(0)
raise SystemExit(1)
PY
}

export B="$B"
tap_send || input tap 540 2100 >>"$LOG" 2>&1 || true
sleep 0.4

# Put prompt in field: clipboard + paste (most reliable for long text)
termux-clipboard-set "$PROMPT" 2>>"$LOG" || true
sleep 0.2
# KEYCODE_PASTE = 279
input keyevent 279 >>"$LOG" 2>&1 || {
  # fallback: short prompt via rish/input text
  if [ "${#PROMPT}" -lt 400 ]; then
    rish -c "input text $(printf '%q' "$PROMPT")" >>"$LOG" 2>&1 || \
    input text "$(echo "$PROMPT" | sed 's/ /%s/g' | head -c 300)" >>"$LOG" 2>&1 || true
  fi
}
sleep 0.5

tap_send || input tap 980 2100 >>"$LOG" 2>&1 || input keyevent 66 >>"$LOG" 2>&1

sha256sum <<<"$PROMPT" | awk '{print $1}' > "$B/meta/last_wired_prompt.sha" 2>/dev/null || true
date +%s > "$B/meta/last_wire_ts"
log "wire sent"
# Reply capture: next ui_dump cycle / consume_response
WIRE
chmod +x "$B/tools/wire_send_ui.sh"
export B="$B"

# --- collab loop: OLD behavior + disk gate ---
cat > "$B/tools/collab_rish_loop.sh" <<'COLLAB'
#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail
B="$HOME/broccoli"
POLL="${COLLAB_POLL_SEC:-12}"
MIN_IDLE="${WIRE_MIN_IDLE_SEC:-3}"
source "$B/lib/disk_gate.sh" 2>/dev/null || true

while true; do
  if command -v disk_ok >/dev/null 2>&1 && ! disk_ok; then
    echo "$(date -Iseconds) disk low" >> "$B/reports/disk_gate.log"
    [ -x "$B/tools/termux_disk_clean.sh" ] && bash "$B/tools/termux_disk_clean.sh" run >>"$B/reports/disk_gate.log" 2>&1 || true
    sleep 30
    continue
  fi

  bash "$B/lib/ui_dump_rish.sh" 2>/dev/null || true
  [ -x "$B/tools/push_chat_lines_to_inbox.sh" ] && bash "$B/tools/push_chat_lines_to_inbox.sh" >>"$B/reports/collab.log" 2>&1 || true
  [ -x "$B/tools/write_sanitized_prompt.sh" ] && bash "$B/tools/write_sanitized_prompt.sh" >>"$B/reports/collab.log" 2>&1 || true

  IDLE="$(bash "$B/lib/user_idle_sec.sh" 2>/dev/null || echo 99)"
  GROK=0
  grep -qiE 'grok|com\.ai\.x\.grok' "$B/reports/ui_dump.xml" 2>/dev/null && GROK=1

  if [ "${IDLE:-0}" -ge "$MIN_IDLE" ] && [ "$GROK" -eq 1 ]; then
    if bash "$B/tools/agent_should_wire.sh" 2>/dev/null; then
      PROMPT="$(cat "$B/reports/SANITIZED_PROMPT.md" 2>/dev/null || true)"
      if [ -n "$PROMPT" ] && [ -x "$B/tools/wire_send_ui.sh" ]; then
        bash "$B/tools/wire_send_ui.sh" "$PROMPT" >>"$B/reports/wire_send.log" 2>&1 || true
        [ -x "$B/tools/agent_consume_iteration.sh" ] && bash "$B/tools/agent_consume_iteration.sh" "$PROMPT" "" >>"$B/reports/agent_consume.log" 2>&1 || true
        [ -s "$B/queue/agent_task.txt" ] && sed -i '1d' "$B/queue/agent_task.txt" 2>/dev/null || : > "$B/queue/agent_task.txt" 2>/dev/null || true
      fi
    fi
  fi
  sleep "$POLL"
done
COLLAB
chmod +x "$B/tools/collab_rish_loop.sh"

# reinit helper
cat > "$B/tools/reinit_agent.sh" <<'RI'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
B="$HOME/broccoli"
[ -x "$B/tools/termux_disk_clean.sh" ] && bash "$B/tools/termux_disk_clean.sh" run >>"$B/reports/reinit.log" 2>&1 || true
pkill -f 'collab_rish_loop|broccoli-daemon|broccoli_worker|watchdog|ui_worker|grok_copilot|agent_handler' 2>/dev/null || true
sleep 2
rm -f "$B/meta/AGENT_STOP" "$B/meta/AGENT_STOP_REQUESTED"
if [ -f "$B/tools/reboot_bootstrap.py" ]; then python3 "$B/tools/reboot_bootstrap.py" >>"$B/reports/reinit.log" 2>&1
else nohup bash "$B/tools/broccoli-daemon.sh" >>"$B/reports/daemon.log" 2>&1 & fi
sleep 2
pgrep -af 'collab_rish_loop|broccoli-daemon|watchdog' || true
echo REINIT_DONE
RI
chmod +x "$B/tools/reinit_agent.sh"

mkdir -p "$HOME/bin"
cat > "$HOME/bin/b" <<'BCLI'
#!/data/data/com.termux/files/usr/bin/bash
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
case "${1:-}" in
  reinit) bash "$HOME/broccoli/tools/reinit_agent.sh" ;;
  wire-test) bash "$HOME/broccoli/tools/wire_send_ui.sh" "${2:-WIRE_TEST: reply OK}" ;;
  agenda) printf '%s\n' "${2:-Run next Broccoli automation step.}" > "$HOME/broccoli/queue/agent_task.txt"; bash "$HOME/broccoli/tools/write_sanitized_prompt.sh"; echo "task queued — collab will wire when idle+grok" ;;
  *) bash "$HOME/broccoli/tools/b_cli.sh" "$@" 2>/dev/null || echo "b reinit | b wire-test | b agenda '...'";;
esac
BCLI
chmod +x "$HOME/bin/b"

echo PATCH_WIRE_AGENDA_RESTORE_OK
