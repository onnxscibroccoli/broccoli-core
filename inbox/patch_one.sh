#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
mkdir -p "$B"/{tools,lib,reports,queue,thread,inbox,prompts,meta,quarantine/staging,bin}
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"

cat > "$B/meta/wire_coords.env" <<'ENV'
COMPOSER_X=540
COMPOSER_Y=1195
SEND_X=1000
SEND_Y=1195
GROK_PKG=com.ai.x.grok
MIN_DUMP_BYTES=8000
COLLAB_POLL_SEC=4
WIRE_MIN_INTERVAL_SEC=18
WIRE_MIN_INTERVAL_TASK_SEC=8
WIRE_MIN_IDLE_SEC=1
MIN_FREE_MB=60
FAST_OPEN_SEC=0.8
FAST_TAP_SEC=0.12
CONSUME_WAIT_SEC=3
ENV

cat > "$B/lib/disk_gate.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
MIN_FREE_MB="${MIN_FREE_MB:-60}"
avail_mb(){ df -k "$HOME" 2>/dev/null | awk 'NR==2{printf "%d", $4/1024}'; }
disk_ok(){ [ "$(avail_mb)" -ge "$MIN_FREE_MB" ]; }
SH
chmod +x "$B/lib/disk_gate.sh"

cat > "$B/lib/timing.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
tms(){ date +%s%3N 2>/dev/null || python3 -c 'import time; print(int(time.time()*1000))'; }
tlog(){
  local phase="$1" t0="$2" t1
  t1=$(tms)
  echo "$(date -Iseconds) LAT ${phase} $((t1-t0))ms" >> "${B:-$HOME/broccoli}/reports/latency.log"
}
SH
chmod +x "$B/lib/timing.sh"

cat > "$B/lib/user_idle_sec.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
echo 99
SH
chmod +x "$B/lib/user_idle_sec.sh"

cat > "$B/lib/ui_dump_rish.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
OUT="$B/reports/ui_dump.xml"
TMP="$B/reports/.ui_dump.tmp"
if command -v rish >/dev/null 2>&1; then
  rish -c 'uiautomator dump /sdcard/ui_dump.xml && cat /sdcard/ui_dump.xml' > "$TMP" 2>/dev/null || true
elif command -v uiautomator >/dev/null 2>&1; then
  uiautomator dump "$TMP" 2>/dev/null || true
else
  exit 1
fi
[ -s "$TMP" ] && mv -f "$TMP" "$OUT"
SH
chmod +x "$B/lib/ui_dump_rish.sh"

cat > "$B/tools/parse_grok_ui.py" <<'PY'
#!/usr/bin/env python3
import json, os, re, sys
from pathlib import Path

def center(b):
    x1, y1, x2, y2 = map(int, b)
    return (x1 + x2) // 2, (y1 + y2) // 2

dump = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "broccoli/reports/ui_dump.xml")
xml = dump.read_text(errors="replace") if dump.is_file() else ""
min_b = int(os.environ.get("MIN_DUMP_BYTES", "8000"))
out = {
    "bytes": len(xml), "package": None, "composer": None, "send": None,
    "composer_text": "", "visible_text": [], "ok": False,
}
m = re.search(r'package="([^"]+)"', xml)
if m:
    out["package"] = m.group(1)
best = None
for m in re.finditer(
    r'class="android\.widget\.EditText"[^>]*(?:text="([^"]*)")?[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
    xml,
):
    t, b = m.group(1) or "", (m.group(2), m.group(3), m.group(4), m.group(5))
    y1 = int(b[0])
    if best is None or y1 > best[0]:
        best = (y1, t, b)
if best:
    cx, cy = center(best[2])
    out["composer"] = {"x": cx, "y": cy}
    out["composer_text"] = best[1]
for pat in (
    r'content-desc="([^"]*send[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
    r'text="Send"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
    r'resource-id="([^"]*send[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
):
    for m in re.finditer(pat, xml, re.I):
        g = m.groups()
        b = g[1:5] if len(g) == 5 else g[0:4]
        out["send"] = {"x": center(b)[0], "y": center(b)[1]}
        break
    if out["send"]:
        break
texts = []
for m in re.finditer(
    r'class="android\.widget\.TextView"[^>]*text="([^"]{4,})"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
    xml,
):
    t, y1 = m.group(1), int(m.group(3))
    if t.strip() and y1 > 200:
        texts.append((y1, t.strip()[:500]))
texts.sort()
out["visible_text"] = [t for _, t in texts[-12:]]
pkg_ok = out["package"] and "grok" in out["package"].lower()
out["ok"] = bool(pkg_ok and out["bytes"] >= min_b and out["composer"])
print(json.dumps(out, ensure_ascii=False))
PY
chmod +x "$B/tools/parse_grok_ui.py"

cat > "$B/tools/push_chat_lines_to_inbox.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
python3 <<'PY'
import json, time
from pathlib import Path
B = Path.home() / "broccoli"
dump = B / "reports/ui_dump.xml"
if not dump.is_file():
    raise SystemExit(0)
import subprocess
r = subprocess.run(
    ["python3", str(B / "tools/parse_grok_ui.py"), str(dump)],
    capture_output=True, text=True, timeout=15,
)
if r.returncode != 0:
    raise SystemExit(0)
d = json.loads(r.stdout or "{}")
lines = d.get("visible_text") or []
if not lines:
    raise SystemExit(0)
inbox = B / "inbox/chat_lines.txt"
new = "\n".join(lines[-8:])[-4000:]
prev = inbox.read_text(errors="replace") if inbox.is_file() else ""
if new.strip() and new.strip() != prev.strip():
    inbox.write_text(new)
    (B / "meta/last_inbox_ts").write_text(str(int(time.time())))
PY
SH
chmod +x "$B/tools/push_chat_lines_to_inbox.sh"

cat > "$B/tools/detect_interject.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml")
HASH=$(printf '%s' "$PARSE" | sha256sum | awk '{print $1}')
LAST="$B/meta/last_ui_chat.hash"
OLD=$(cat "$LAST" 2>/dev/null || echo "")
printf '%s' "$HASH" > "$LAST"
CT=$(printf '%s' "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('composer_text') or '').strip())")
[ -n "$CT" ] && exit 1
[ "$HASH" = "$OLD" ] && exit 1
[ -s "$B/queue/agent_task.txt" ] && exit 0
printf '%s' "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); t=d.get('visible_text') or []; raise SystemExit(0 if t else 1)"
SH
chmod +x "$B/tools/detect_interject.sh"

cat > "$B/prompts/agent_turn.txt" <<'TXT'
You are Broccoli on this phone. One concrete step. Short.
Context:
{{CONTEXT}}
Task:
{{TASK}}
TXT

cat > "$B/tools/write_sanitized_prompt.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
OUT="$B/reports/SANITIZED_PROMPT.md"
TASK=""
[ -s "$B/queue/agent_task.txt" ] && TASK="$(head -c 900 "$B/queue/agent_task.txt")"
ROLL=""
[ -f "$B/thread/rolling_summary.txt" ] && ROLL="$(head -c 700 "$B/thread/rolling_summary.txt")"
CONV=""
[ -f "$B/inbox/chat_lines.txt" ] && CONV="$(tail -20 "$B/inbox/chat_lines.txt" | head -c 1800)"
TPL="$(cat "$B/prompts/agent_turn.txt")"
BODY="${TPL//\{\{CONTEXT\}\}/${ROLL}

UI:
${CONV}}"
BODY="${BODY//\{\{TASK\}\}/${TASK:-Interject: help user, advance agenda.}}"
printf '%s' "$BODY" | head -c 3500 > "$OUT"
SH
chmod +x "$B/tools/write_sanitized_prompt.sh"

cat > "$B/tools/agent_should_wire.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
# shellcheck source=/dev/null
source "$B/meta/wire_coords.env"
NOW=$(date +%s)
LAST=$(cat "$B/meta/last_wire_ts" 2>/dev/null || echo 0)
if [ -s "$B/queue/agent_task.txt" ]; then MIN="${WIRE_MIN_INTERVAL_TASK_SEC:-8}"
else MIN="${WIRE_MIN_INTERVAL_SEC:-18}"; fi
[ $((NOW - LAST)) -lt "$MIN" ] && exit 1
[ -f "$B/reports/ui_dump.xml" ] || exit 1
PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml")
printf '%s' "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); raise SystemExit(0 if d.get('ok') else 1)" || exit 1
CT=$(printf '%s' "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('composer_text') or '').strip())")
[ -n "$CT" ] && exit 1
[ -s "$B/queue/agent_task.txt" ] && exit 0
bash "$B/tools/detect_interject.sh" 2>/dev/null && exit 0
P="$B/reports/SANITIZED_PROMPT.md"
H="$B/meta/last_wired_prompt.sha"
[ -f "$P" ] || exit 1
CUR=$(sha256sum "$P" | awk '{print $1}')
OLD=$(cat "$H" 2>/dev/null || echo "")
[ "$CUR" != "$OLD" ] && exit 0
exit 1
SH
chmod +x "$B/tools/agent_should_wire.sh"

cat > "$B/tools/wire_send_ui.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
LOG="$B/reports/wire_send.log"
PROMPT="${1:-}"
[ -n "$PROMPT" ] || exit 1
# shellcheck source=/dev/null
source "$B/meta/wire_coords.env"
# shellcheck source=/dev/null
source "$B/lib/timing.sh"
T0=$(tms)
log(){ echo "$(date -Iseconds) $*" >>"$LOG"; }
log "SEND start len=${#PROMPT}"
on_grok(){ [ -f "$B/reports/ui_dump.xml" ] && grep -qi "${GROK_PKG}" "$B/reports/ui_dump.xml" 2>/dev/null; }
if ! on_grok; then
  monkey -p "${GROK_PKG}" -c android.intent.category.LAUNCHER 1 >>"$LOG" 2>&1 || true
  sleep "${FAST_OPEN_SEC:-0.8}"
fi
tlog open_grok "$T0"
TD=$(tms)
bash "$B/lib/ui_dump_rish.sh" >>"$LOG" 2>&1 || { log "dump fail"; exit 1; }
tlog ui_dump "$TD"
PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml")
log "dump_bytes=$(printf '%s' "$PARSE" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("bytes",0))')"
OK=$(printf '%s' "$PARSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok'))")
tap(){ input tap "$1" "$2"; echo "TAP $1 $2" >>"$LOG"; sleep "${FAST_TAP_SEC:-0.12}"; }
if [ "$OK" != "True" ]; then
  tap "${COMPOSER_X}" "${COMPOSER_Y}"
  TD=$(tms)
  bash "$B/lib/ui_dump_rish.sh" >>"$LOG" 2>&1 || true
  tlog ui_dump_retry "$TD"
  PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml")
  OK=$(printf '%s' "$PARSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok'))")
fi
[ "$OK" != "True" ] && { log '{"err":"no_composer"}'; exit 1; }
CX=$(printf '%s' "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['composer']['x'])")
CY=$(printf '%s' "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['composer']['y'])")
TT=$(tms); tap "$CX" "$CY"; tlog tap_composer "$TT"
termux-clipboard-set "$PROMPT" >>"$LOG" 2>&1 || true
input keyevent 279 >>"$LOG" 2>&1 || true
sleep 0.22
tlog paste "$TT"
SX=$(printf '%s' "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('send'); print(s['x'] if s else '')" 2>/dev/null || true)
SY=$(printf '%s' "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('send'); print(s['y'] if s else '')" 2>/dev/null || true)
TS=$(tms)
if [ -n "$SX" ] && [ -n "$SY" ]; then tap "$SX" "$SY"; else tap "${SEND_X}" "${SEND_Y}"; fi
tlog tap_send "$TS"
sha256sum <<<"$PROMPT" | awk '{print $1}' > "$B/meta/last_wired_prompt.sha"
date +%s > "$B/meta/last_wire_ts"
log "send_ok"
tlog wire_total "$T0"
SH
chmod +x "$B/tools/wire_send_ui.sh"

cat > "$B/tools/consume_response.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
python3 <<'PY'
import json, time, subprocess
from pathlib import Path
B = Path.home() / "broccoli"
dump = B / "reports/ui_dump.xml"
r = subprocess.run(["python3", str(B / "tools/parse_grok_ui.py"), str(dump)], capture_output=True, text=True)
if r.returncode != 0:
    raise SystemExit(0)
d = json.loads(r.stdout or "{}")
lines = d.get("visible_text") or []
if not lines:
    raise SystemExit(0)
last = lines[-1][:2000]
rec = {"ts": time.time(), "role": "assistant", "text": last}
with (B / "thread/conversation.jsonl").open("a") as f:
    f.write(json.dumps(rec) + "\n")
(B / "thread/rolling_summary.txt").write_text(last[:800])
PY
SH
chmod +x "$B/tools/consume_response.sh"

cat > "$B/tools/agent_consume_iteration.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
# shellcheck source=/dev/null
source "$B/meta/wire_coords.env"
sleep "${CONSUME_WAIT_SEC:-3}"
bash "$B/lib/ui_dump_rish.sh" 2>/dev/null || true
bash "$B/tools/consume_response.sh" 2>/dev/null || true
SH
chmod +x "$B/tools/agent_consume_iteration.sh"

cat > "$B/tools/agent_health.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
python3 <<'PY'
import json, subprocess, time
from pathlib import Path
B = Path.home() / "broccoli"
dump = B / "reports/ui_dump.xml"
parse = {}
if dump.is_file():
    r = subprocess.run(["python3", str(B / "tools/parse_grok_ui.py"), str(dump)], capture_output=True, text=True, timeout=20)
    if r.returncode == 0:
        parse = json.loads(r.stdout or "{}")
def pg(p):
    try:
        return subprocess.run(["pgrep", "-af", p], capture_output=True, text=True, timeout=2).stdout.strip().splitlines()[:2]
    except Exception:
        return []
df = subprocess.run("df -k $HOME | awk 'NR==2{print int($4/1024)}'", shell=True, capture_output=True, text=True)
h = {
    "ts": time.time(),
    "avail_mb": df.stdout.strip(),
    "collab": pg("collab_rish_loop"),
    "daemon": pg("broccoli-daemon"),
    "dump_ok": parse.get("ok"),
    "dump_bytes": parse.get("bytes"),
    "composer": bool(parse.get("composer")),
    "task_queued": (B / "queue/agent_task.txt").is_file() and (B / "queue/agent_task.txt").stat().st_size > 0,
}
(B / "meta/agent_health.json").write_text(json.dumps(h, indent=2))
print(json.dumps(h))
PY
SH
chmod +x "$B/tools/agent_health.sh"

cat > "$B/tools/collab_rish_loop.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -u
B="$HOME/broccoli"
# shellcheck source=/dev/null
source "$B/meta/wire_coords.env" 2>/dev/null || true
# shellcheck source=/dev/null
source "$B/lib/disk_gate.sh" 2>/dev/null || true
# shellcheck source=/dev/null
source "$B/lib/timing.sh" 2>/dev/null || true
POLL="${COLLAB_POLL_SEC:-4}"
MIN_IDLE="${WIRE_MIN_IDLE_SEC:-1}"
LAST_HASH=""
while true; do
  LOOP0=$(tms)
  if command -v disk_ok >/dev/null 2>&1 && ! disk_ok; then
    echo "$(date -Iseconds) disk low avail=$(avail_mb 2>/dev/null || echo ?)MB" >>"$B/reports/disk_gate.log"
    [ -x "$B/tools/termux_disk_clean.sh" ] && bash "$B/tools/termux_disk_clean.sh" run >>"$B/reports/disk_gate.log" 2>&1 || true
    sleep 15
    continue
  fi
  TD=$(tms)
  bash "$B/lib/ui_dump_rish.sh" 2>/dev/null || true
  tlog collab_dump "$TD"
  bash "$B/tools/push_chat_lines_to_inbox.sh" 2>/dev/null || true
  DH=$(sha256sum "$B/reports/ui_dump.xml" 2>/dev/null | awk '{print $1}' || echo x)
  if [ "$DH" != "$LAST_HASH" ] || [ -s "$B/queue/agent_task.txt" ]; then
    bash "$B/tools/write_sanitized_prompt.sh" 2>/dev/null || true
    LAST_HASH="$DH"
  fi
  bash "$B/tools/agent_health.sh" >>"$B/reports/health.log" 2>/dev/null || true
  IDLE=$(bash "$B/lib/user_idle_sec.sh" 2>/dev/null || echo 99)
  GROK=0
  grep -qi grok "$B/reports/ui_dump.xml" 2>/dev/null && GROK=1
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
SH
chmod +x "$B/tools/collab_rish_loop.sh"

cat > "$B/tools/broccoli_worker.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
Q="$B/queue/pending.txt"
[ -s "$Q" ] || exit 0
LINE=$(head -1 "$Q")
sed -i '1d' "$Q" 2>/dev/null || true
eval "$LINE" >>"$B/reports/worker.log" 2>&1 || true
SH
chmod +x "$B/tools/broccoli_worker.sh"

cat > "$B/tools/broccoli-daemon.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
echo "$(date -Iseconds) daemon start" >>"$B/reports/daemon.log"
bash "$B/tools/collab_rish_loop.sh" >>"$B/reports/collab.log" 2>&1 &
PID=$!
while true; do
  bash "$B/tools/broccoli_worker.sh" 2>/dev/null || true
  kill -0 "$PID" 2>/dev/null || { bash "$B/tools/collab_rish_loop.sh" >>"$B/reports/collab.log" 2>&1 & PID=$!; }
  sleep 10
done
SH
chmod +x "$B/tools/broccoli-daemon.sh"

cat > "$B/tools/reinit_agent.sh" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
B="$HOME/broccoli"
[ -x "$B/tools/termux_disk_clean.sh" ] && bash "$B/tools/termux_disk_clean.sh" run >>"$B/reports/reinit.log" 2>&1 || true
pkill -f 'collab_rish_loop|broccoli-daemon|broccoli_worker|watchdog|ui_worker|grok_copilot|agent_handler' 2>/dev/null || true
sleep 2
rm -f "$B/meta/AGENT_STOP" "$B/meta/AGENT_STOP_REQUESTED"
if [ -f "$B/tools/reboot_bootstrap.py" ]; then
  python3 "$B/tools/reboot_bootstrap.py" >>"$B/reports/reinit.log" 2>&1
else
  nohup bash "$B/tools/broccoli-daemon.sh" >>"$B/reports/daemon.log" 2>&1 &
fi
sleep 2
pgrep -af 'collab_rish_loop|broccoli-daemon|watchdog' || true
df -h "$HOME" | tail -1
SH
chmod +x "$B/tools/reinit_agent.sh"

mkdir -p "$HOME/bin"
cat > "$HOME/bin/b" <<'SH'
#!/data/data/com.termux/files/usr/bin/bash
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
B="$HOME/broccoli"
case "${1:-}" in
  reinit) bash "$B/tools/reinit_agent.sh" ;;
  health) bash "$B/tools/agent_health.sh" ;;
  latency) grep LAT "$B/reports/latency.log" 2>/dev/null | tail -30 ;;
  wire-debug) bash "$B/lib/ui_dump_rish.sh"; python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml" ;;
  wire-test) bash "$B/tools/wire_send_ui.sh" "${2:-WIRE_OK}"; grep LAT "$B/reports/latency.log" | tail -8 ;;
  interject) printf '%s\n' "${2:-Broccoli check-in.}" > "$B/queue/agent_task.txt"; bash "$B/tools/write_sanitized_prompt.sh"; echo queued ;;
  status) bash "$B/tools/agent_health.sh"; pgrep -af 'collab_rish_loop|broccoli-daemon' || true ;;
  *) bash "$B/tools/b_cli.sh" "$@" 2>/dev/null || echo "b reinit|status|health|latency|wire-debug|wire-test|interject" ;;
esac
SH
chmod +x "$HOME/bin/b"
grep -q 'HOME/bin' ~/.bashrc 2>/dev/null || echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc

pkill -f 'collab_rish_loop|broccoli-daemon' 2>/dev/null || true
sleep 1
bash "$B/tools/reinit_agent.sh"
echo OK
