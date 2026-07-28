#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
mkdir -p "$B"/{tools,lib,meta,reports}

cat > "$B/meta/wire_coords.env" <<'ENV'
COMPOSER_X=540
COMPOSER_Y=1195
SEND_X=1000
SEND_Y=1195
GROK_PKG=com.ai.x.grok
MIN_DUMP_BYTES=8000
# TURBO defaults (override with b turbo-off)
COLLAB_POLL_SEC=4
WIRE_MIN_INTERVAL_SEC=18
WIRE_MIN_INTERVAL_TASK_SEC=8
WIRE_MIN_IDLE_SEC=1
MIN_FREE_MB=60
FAST_OPEN_SEC=0.8
FAST_TAP_MS=0.15
CONSUME_WAIT_SEC=3
ENV

cat > "$B/lib/timing.sh" <<'T'
#!/data/data/com.termux/files/usr/bin/bash
# usage: t0=$(tms); ...; tlog phase "$t0"
tms(){ date +%s%3N 2>/dev/null || python3 -c 'import time; print(int(time.time()*1000))'; }
tlog(){
  local phase="$1" t0="$2"
  local t1; t1=$(tms)
  echo "$(date -Iseconds) LAT ${phase} $((t1-t0))ms" >> "${B:-$HOME/broccoli}/reports/latency.log"
}
T
chmod +x "$B/lib/timing.sh"

cat > "$B/tools/agent_health.sh" <<'H'
#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
PARSE='{}'
[ -f "$B/reports/ui_dump.xml" ] && PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml" 2>/dev/null || echo '{}')
python3 <<PY
import json, os, time, subprocess
from pathlib import Path
B = Path.home()/"broccoli"
parse = json.loads("""$PARSE""".replace('"""',''))
def pgrep(p):
    try:
        r = subprocess.run(["pgrep","-af",p], capture_output=True, text=True, timeout=2)
        return r.stdout.strip().splitlines()[:3]
    except: return []
h = {
  "ts": time.time(),
  "avail_mb": subprocess.run("df -k $HOME|awk 'NR==2{print int($4/1024)}'", shell=True, capture_output=True, text=True).stdout.strip(),
  "collab": pgrep("collab_rish_loop"),
  "daemon": pgrep("broccoli-daemon"),
  "dump_ok": parse.get("ok"),
  "dump_bytes": parse.get("bytes"),
  "composer": bool(parse.get("composer")),
  "last_wire_ts": (B/"meta/last_wire_ts").read_text().strip() if (B/"meta/last_wire_ts").is_file() else "",
  "task_queued": (B/"queue/agent_task.txt").is_file() and (B/"queue/agent_task.txt").stat().st_size>0,
}
(B/"meta/agent_health.json").write_text(json.dumps(h, indent=2))
print(json.dumps(h))
PY
H
chmod +x "$B/tools/agent_health.sh"

# Fast wire: no monkey if already grok; one dump; minimal sleep
cat > "$B/tools/wire_send_ui.sh" <<'WIRE'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
LOG="$B/reports/wire_send.log"
LAT="$B/reports/latency.log"
PROMPT="${1:-}"; [ -n "$PROMPT" ] || exit 1
source "$B/meta/wire_coords.env"
source "$B/lib/timing.sh"
T0=$(tms)
log(){ echo "$(date -Iseconds) $*" >>"$LOG"; }
log "SEND start len=${#PROMPT}"

on_grok(){
  [ -f "$B/reports/ui_dump.xml" ] && grep -qi "${GROK_PKG}" "$B/reports/ui_dump.xml" 2>/dev/null
}

if ! on_grok; then
  monkey -p "${GROK_PKG}" -c android.intent.category.LAUNCHER 1 >>"$LOG" 2>&1 || true
  sleep "${FAST_OPEN_SEC:-0.8}"
fi
tlog open_grok "$T0"

TD=$(tms)
bash "$B/lib/ui_dump_rish.sh" >>"$LOG" 2>&1 || { log "dump fail"; exit 1; }
tlog ui_dump "$TD"

PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml")
log "dump_bytes=$(echo "$PARSE"|python3 -c 'import sys,json; print(json.load(sys.stdin).get("bytes",0))')"
OK=$(echo "$PARSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok'))")

tap(){ input tap "$1" "$2"; echo "TAP $1 $2" >>"$LOG"; sleep "${FAST_TAP_MS:-0.15}"; }

if [ "$OK" != "True" ]; then
  tap "${COMPOSER_X}" "${COMPOSER_Y}"
  TD=$(tms)
  bash "$B/lib/ui_dump_rish.sh" >>"$LOG" 2>&1 || true
  tlog ui_dump_retry "$TD"
  PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml")
  OK=$(echo "$PARSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok'))")
fi
[ "$OK" != "True" ] && { log '{"err":"no_composer"}'; exit 1; }

CX=$(echo "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['composer']['x'])")
CY=$(echo "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['composer']['y'])")
TT=$(tms); tap "$CX" "$CY"; tlog tap_composer "$TT"

termux-clipboard-set "$PROMPT" >>"$LOG" 2>&1
input keyevent 279 >>"$LOG" 2>&1
sleep 0.25
tlog paste "$TT"

SX=$(echo "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('send'); print(s['x'] if s else '')" 2>/dev/null || true)
SY=$(echo "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('send'); print(s['y'] if s else '')" 2>/dev/null || true)
TS=$(tms)
[ -n "$SX" ] && tap "$SX" "$SY" || tap "${SEND_X}" "${SEND_Y}"
tlog tap_send "$TS"

sha256sum <<<"$PROMPT" | awk '{print $1}' > "$B/meta/last_wired_prompt.sha"
date +%s > "$B/meta/last_wire_ts"
log "send_ok"
tlog wire_total "$T0"
WIRE
chmod +x "$B/tools/wire_send_ui.sh"

cat > "$B/tools/agent_should_wire.sh" <<'SW'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
source "$B/meta/wire_coords.env"
NOW=$(date +%s)
LAST=$(cat "$B/meta/last_wire_ts" 2>/dev/null || echo 0)
if [ -s "$B/queue/agent_task.txt" ]; then MIN=${WIRE_MIN_INTERVAL_TASK_SEC:-8}
else MIN=${WIRE_MIN_INTERVAL_SEC:-18}; fi
[ $((NOW-LAST)) -lt "$MIN" ] && exit 1
[ -f "$B/reports/ui_dump.xml" ] || exit 1
PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml")
echo "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('ok') else 1)" || exit 1
CT=$(echo "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('composer_text') or '').strip())")
[ -n "$CT" ] && exit 1
[ -s "$B/queue/agent_task.txt" ] && exit 0
bash "$B/tools/detect_interject.sh" 2>/dev/null && exit 0
P="$B/reports/SANITIZED_PROMPT.md"; H="$B/meta/last_wired_prompt.sha"
[ -f "$P" ] || exit 1
CUR=$(sha256sum "$P" | awk '{print $1}'); OLD=$(cat "$H" 2>/dev/null || echo "")
[ "$CUR" != "$OLD" ] && exit 0
exit 1
SW
chmod +x "$B/tools/agent_should_wire.sh"

cat > "$B/tools/agent_consume_iteration.sh" <<'AC'
#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
source "$B/meta/wire_coords.env"
W="${CONSUME_WAIT_SEC:-3}"
sleep "$W"
bash "$B/lib/ui_dump_rish.sh" 2>/dev/null || true
bash "$B/tools/consume_response.sh" 2>/dev/null || true
AC
chmod +x "$B/tools/agent_consume_iteration.sh"

cat > "$B/tools/collab_rish_loop.sh" <<'COLLAB'
#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail
B="$HOME/broccoli"
source "$B/meta/wire_coords.env" 2>/dev/null || true
source "$B/lib/disk_gate.sh" 2>/dev/null || true
source "$B/lib/timing.sh" 2>/dev/null || true
POLL="${COLLAB_POLL_SEC:-4}"
MIN_IDLE="${WIRE_MIN_IDLE_SEC:-1}"
LAST_PROMPT_HASH=""
while true; do
  LOOP0=$(tms)
  if ! disk_ok 2>/dev/null; then
    echo "$(date -Iseconds) disk low" >>"$B/reports/disk_gate.log"
    [ -x "$B/tools/termux_disk_clean.sh" ] && bash "$B/tools/termux_disk_clean.sh" run >>"$B/reports/disk_gate.log" 2>&1 || true
    sleep 15
    continue
  fi
  TD=$(tms)
  bash "$B/lib/ui_dump_rish.sh" 2>/dev/null || true
  tlog collab_dump "$TD"

  bash "$B/tools/push_chat_lines_to_inbox.sh" 2>/dev/null || true
  PH=$(sha256sum "$B/reports/ui_dump.xml" 2>/dev/null | awk '{print $1}' || echo x)
  if [ "$PH" != "$LAST_PROMPT_HASH" ] || [ -s "$B/queue/agent_task.txt" ]; then
    bash "$B/tools/write_sanitized_prompt.sh" 2>/dev/null || true
    LAST_PROMPT_HASH="$PH"
  fi
  bash "$B/tools/agent_health.sh" >>"$B/reports/health.log" 2>/dev/null || true

  IDLE=$(bash "$B/lib/user_idle_sec.sh" 2>/dev/null || echo 99)
  GROK=0; grep -qi grok "$B/reports/ui_dump.xml" 2>/dev/null && GROK=1
  if [ "$GROK" -eq 1 ] && [ "${IDLE:-0}" -ge "$MIN_IDLE" ]; then
    if bash "$B/tools/agent_should_wire.sh" 2>/dev/null; then
      PROMPT=$(cat "$B/reports/SANITIZED_PROMPT.md" 2>/dev/null || true)
      if [ -n "$PROMPT" ]; then
        TW=$(tms)
        bash "$B/tools/wire_send_ui.sh" "$PROMPT" >>"$B/reports/wire_send.log" 2>&1 || true
        tlog collab_wire "$TW"
        bash "$B/tools/agent_consume_iteration.sh" >>"$B/reports/agent_consume.log" 2>&1 &
        [ -s "$B/queue/agent_task.txt" ] && : > "$B/queue/agent_task.txt" || true
      fi
    fi
  fi
  tlog collab_loop "$LOOP0"
  sleep "$POLL"
done
COLLAB
chmod +x "$B/tools/collab_rish_loop.sh"

cat > "$B/tools/broccoli-daemon.sh" <<'DM'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
bash "$B/tools/collab_rish_loop.sh" >>"$B/reports/collab.log" 2>&1 &
COLLAB_PID=$!
while true; do
  bash "$B/tools/broccoli_worker.sh" 2>/dev/null || true
  kill -0 "$COLLAB_PID" 2>/dev/null || { bash "$B/tools/collab_rish_loop.sh" >>"$B/reports/collab.log" 2>&1 & COLLAB_PID=$!; }
  sleep 10
done
DM
chmod +x "$B/tools/broccoli-daemon.sh"

mkdir -p "$HOME/bin"
cat > "$HOME/bin/b" <<'BCLI'
#!/data/data/com.termux/files/usr/bin/bash
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
B="$HOME/broccoli"
case "${1:-}" in
  reinit) bash "$B/tools/reinit_agent.sh" ;;
  latency) echo "=== last wire timings ==="; grep LAT "$B/reports/latency.log" 2>/dev/null | tail -25
           echo "=== last loops ==="; grep 'collab_loop\|collab_wire' "$B/reports/latency.log" 2>/dev/null | tail -15;;
  health) bash "$B/tools/agent_health.sh" | python3 -m json.tool 2>/dev/null || bash "$B/tools/agent_health.sh";;
  turbo-off)
    sed -i 's/COLLAB_POLL_SEC=4/COLLAB_POLL_SEC=12/; s/WIRE_MIN_INTERVAL_SEC=18/WIRE_MIN_INTERVAL_SEC=45/' "$B/meta/wire_coords.env" 2>/dev/null || true
    echo "turbo off";;
  turbo-on)
    sed -i 's/COLLAB_POLL_SEC=12/COLLAB_POLL_SEC=4/; s/WIRE_MIN_INTERVAL_SEC=45/WIRE_MIN_INTERVAL_SEC=18/' "$B/meta/wire_coords.env" 2>/dev/null || true
    echo "turbo on";;
  wire-test) bash "$B/tools/wire_send_ui.sh" "${2:-WIRE_OK}"; b latency;;
  interject) printf '%s\n' "${2:-Broccoli turbo check.}" > "$B/queue/agent_task.txt"; bash "$B/tools/write_sanitized_prompt.sh"; echo "task queued (wires in ~8s if Grok open)";;
  status) b health; pgrep -af 'collab|broccoli-daemon'||true;;
  *) bash "$B/tools/b_cli.sh" "$@" 2>/dev/null || echo "b reinit|health|latency|wire-test|interject|turbo-on";;
esac
BCLI
chmod +x "$HOME/bin/b"

echo PATCH_TURBO_OK
