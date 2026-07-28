#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
mkdir -p "$B"/{tools,lib,reports,queue,thread,inbox,prompts,meta,quarantine/staging,bin}

# --- coords from your working log ---
cat > "$B/meta/wire_coords.env" <<'ENV'
COMPOSER_X=540
COMPOSER_Y=1195
SEND_X=1000
SEND_Y=1195
GROK_PKG=com.ai.x.grok
MIN_DUMP_BYTES=12000
WIRE_MIN_INTERVAL_SEC=45
WIRE_MIN_IDLE_SEC=3
COLLAB_POLL_SEC=12
MIN_FREE_MB=80
ENV

cat > "$B/lib/disk_gate.sh" <<'DG'
#!/data/data/com.termux/files/usr/bin/bash
MIN_FREE_MB="${MIN_FREE_MB:-80}"
avail_mb(){ df -k "$HOME" 2>/dev/null | awk 'NR==2{printf "%d", $4/1024}'; }
disk_ok(){ [ "$(avail_mb)" -ge "$MIN_FREE_MB" ]; }
DG
chmod +x "$B/lib/disk_gate.sh"

cat > "$B/lib/user_idle_sec.sh" <<'IDLE'
#!/data/data/com.termux/files/usr/bin/bash
echo 99
IDLE
chmod +x "$B/lib/user_idle_sec.sh"

cat > "$B/lib/ui_dump_rish.sh" <<'DUMP'
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
[ -s "$TMP" ] && mv -f "$TMP" "$OUT" || exit 1
DUMP
chmod +x "$B/lib/ui_dump_rish.sh"

cat > "$B/tools/parse_grok_ui.py" <<'PY'
#!/usr/bin/env python3
import re, sys, json, os
from pathlib import Path
dump = Path(sys.argv[1] if len(sys.argv)>1 else Path.home()/"broccoli/reports/ui_dump.xml")
xml = dump.read_text(errors="replace") if dump.is_file() else ""
min_b = int(os.environ.get("MIN_DUMP_BYTES","8000"))
out = {"bytes": len(xml), "package": None, "composer": None, "send": None,
       "user_lines": [], "assistant_lines": [], "composer_text": "", "ok": False}
m = re.search(r'package="([^"]+)"', xml)
if m: out["package"] = m.group(1)
def center(b):
    x1,y1,x2,y2 = map(int, b); return (x1+x2)//2,(y1+y2)//2
best = None
for m in re.finditer(r'class="android\.widget\.EditText"[^>]*(?:text="([^"]*)")?[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
    t, b = m.group(1) or "", (m.group(2),m.group(3),m.group(4),m.group(5))
    y1 = int(b[0])
    if best is None or y1 > best[0]: best = (y1, t, b)
if best:
    cx,cy = center(best[2]); out["composer"] = {"x":cx,"y":cy,"text":best[1]}
    out["composer_text"] = best[1]
for pat in [r'content-desc="([^"]*send[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
            r'text="Send"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
            r'resource-id="([^"]*send[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"']:
    for m in re.finditer(pat, xml, re.I):
        g = m.groups()
        b = g[1:5] if len(g)==5 else g[0:4]
        out["send"] = {"x":center(b)[0],"y":center(b)[1]}; break
    if out["send"]: break
# Chat-like TextViews (heuristic)
texts = []
for m in re.finditer(r'class="android\.widget\.TextView"[^>]*text="([^"]{4,})"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
    t,y1 = m.group(1), int(m.group(3))
    if t.strip() and y1 > 200: texts.append((y1, t.strip()[:500]))
texts.sort()
out["visible_text"] = [t for _,t in texts[-12:]]
pkg_ok = out["package"] and "grok" in out["package"].lower()
out["ok"] = bool(pkg_ok and out["bytes"]>=min_b and out["composer"])
print(json.dumps(out, ensure_ascii=False))
PY
chmod +x "$B/tools/parse_grok_ui.py"

cat > "$B/tools/push_chat_lines_to_inbox.sh" <<'PUSH'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml" 2>/dev/null || echo '{}')
python3 <<PY
import json, os
from pathlib import Path
B = Path.home()/"broccoli"
p = json.loads("""$PARSE""".replace('"""',''))
lines = p.get("visible_text") or []
if not lines: raise SystemExit(0)
inbox = B/"inbox/chat_lines.txt"
prev = inbox.read_text(errors="replace") if inbox.is_file() else ""
new = "\\n".join(lines[-8:])
if new.strip() and new.strip() != prev.strip():
    inbox.write_text(new[-4000:])
    (B/"meta/last_inbox_ts").write_text(str(int(__import__("time").time())))
PY
PUSH
chmod +x "$B/tools/push_chat_lines_to_inbox.sh"

cat > "$B/tools/detect_interject.sh" <<'DET'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml")
HASH=$(echo "$PARSE" | sha256sum | awk '{print $1}')
LAST="$B/meta/last_ui_chat.hash"
OLD=$(cat "$LAST" 2>/dev/null || echo "")
echo "$HASH" > "$LAST"
# interject if visible chat changed and composer not mid-type
COMP=$(echo "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('composer_text') or '').strip())" 2>/dev/null || echo "")
[ -n "$COMP" ] && exit 1
[ "$HASH" = "$OLD" ] && exit 1
[ -s "$B/queue/agent_task.txt" ] && exit 0
echo "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); t=d.get('visible_text') or []; exit(0 if len(t)>=1 else 1)"
DET
chmod +x "$B/tools/detect_interject.sh"

cat > "$B/prompts/agent_turn.txt" <<'TPL'
You are Broccoli — alive automation on this phone. Be concise, one concrete next step.
Context:
{{CONTEXT}}
Task:
{{TASK}}
Reply in chat; no vault paths; no huge paste blocks.
TPL

cat > "$B/tools/write_sanitized_prompt.sh" <<'WSP'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
OUT="$B/reports/SANITIZED_PROMPT.md"
TASK=""; [ -s "$B/queue/agent_task.txt" ] && TASK="$(head -c 900 "$B/queue/agent_task.txt")"
ROLL=""; [ -f "$B/thread/rolling_summary.txt" ] && ROLL="$(head -c 700 "$B/thread/rolling_summary.txt")"
CONV=""; [ -f "$B/inbox/chat_lines.txt" ] && CONV="$(tail -20 "$B/inbox/chat_lines.txt" | head -c 1800)"
TPL="$(cat "$B/prompts/agent_turn.txt")"
BODY="${TPL//\{\{CONTEXT\}\}/${ROLL}

Recent UI chat:
${CONV}}"
BODY="${BODY//\{\{TASK\}\}/${TASK:-Interject helpfully: acknowledge user, advance Broccoli agenda.}}"
printf '%s' "$BODY" | head -c 3500 > "$OUT"
WSP
chmod +x "$B/tools/write_sanitized_prompt.sh"

cat > "$B/tools/agent_should_wire.sh" <<'SW'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
source "$B/meta/wire_coords.env" 2>/dev/null || true
NOW=$(date +%s)
LAST=$(cat "$B/meta/last_wire_ts" 2>/dev/null || echo 0)
MIN=${WIRE_MIN_INTERVAL_SEC:-45}
[ $((NOW-LAST)) -lt "$MIN" ] && [ ! -s "$B/queue/agent_task.txt" ] && exit 1
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

cat > "$B/tools/wire_send_ui.sh" <<'WIRE'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
LOG="$B/reports/wire_send.log"
PROMPT="${1:-}"; [ -n "$PROMPT" ] || exit 1
source "$B/meta/wire_coords.env"
log(){ echo "$(date -Iseconds) $*" >>"$LOG"; }
log "SEND start len=${#PROMPT}"
monkey -p "${GROK_PKG}" -c android.intent.category.LAUNCHER 1 >>"$LOG" 2>&1 || true
sleep 2
dump(){ bash "$B/lib/ui_dump_rish.sh" >>"$LOG" 2>&1 || { log "dump fail"; return 1; }
  log "dump_bytes=$(wc -c <"$B/reports/ui_dump.xml")"
  python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml" >>"$LOG"
}
tap(){ echo "TAP $1 $2" >>"$LOG"; input tap "$1" "$2"; }
PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml" 2>/dev/null || echo '{"ok":false}')
OK=$(echo "$PARSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok'))")
if [ "$OK" != "True" ]; then dump || true; PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml"); tap "${COMPOSER_X}" "${COMPOSER_Y}"; sleep 0.5; dump || true; PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml"); fi
OK=$(echo "$PARSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok'))")
[ "$OK" != "True" ] && { log '{"err":"no_composer"}'; exit 1; }
CX=$(echo "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['composer']['x'])")
CY=$(echo "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['composer']['y'])")
tap "$CX" "$CY"; sleep 0.35
termux-clipboard-set "$PROMPT" >>"$LOG" 2>&1; sleep 0.2; input keyevent 279 >>"$LOG" 2>&1; sleep 0.45
SX=$(echo "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('send'); print(s['x'] if s else '')" 2>/dev/null || true)
SY=$(echo "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('send'); print(s['y'] if s else '')" 2>/dev/null || true)
[ -n "$SX" ] && tap "$SX" "$SY" || tap "${SEND_X}" "${SEND_Y}"
sha256sum <<<"$PROMPT" | awk '{print $1}' > "$B/meta/last_wired_prompt.sha"
date +%s > "$B/meta/last_wire_ts"
log "send_ok"
WIRE
chmod +x "$B/tools/wire_send_ui.sh"

cat > "$B/tools/consume_response.sh" <<'CON'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml" 2>/dev/null || echo '{}')
python3 <<PY
import json, time
from pathlib import Path
B = Path.home()/"broccoli"
d = json.loads("""$PARSE""".replace('"""',''))
lines = d.get("visible_text") or []
if not lines: raise SystemExit(0)
last = lines[-1][:2000]
rec = {"ts": time.time(), "role": "assistant", "text": last}
with (B/"thread/conversation.jsonl").open("a") as f:
    f.write(json.dumps(rec)+"\n")
(B/"thread/rolling_summary.txt").write_text(last[:800])
PY
CON
chmod +x "$B/tools/consume_response.sh"

cat > "$B/tools/agent_consume_iteration.sh" <<'AC'
#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
sleep 8
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
POLL="${COLLAB_POLL_SEC:-12}"
MIN_IDLE="${WIRE_MIN_IDLE_SEC:-3}"
while true; do
  if ! disk_ok 2>/dev/null; then
    echo "$(date -Iseconds) disk low avail=$(avail_mb)MB" >>"$B/reports/disk_gate.log"
    [ -x "$B/tools/termux_disk_clean.sh" ] && bash "$B/tools/termux_disk_clean.sh" run >>"$B/reports/disk_gate.log" 2>&1 || true
    sleep 30; continue
  fi
  bash "$B/lib/ui_dump_rish.sh" 2>/dev/null || true
  bash "$B/tools/push_chat_lines_to_inbox.sh" 2>/dev/null || true
  bash "$B/tools/write_sanitized_prompt.sh" 2>/dev/null || true
  IDLE=$(bash "$B/lib/user_idle_sec.sh" 2>/dev/null || echo 99)
  GROK=0; grep -qi grok "$B/reports/ui_dump.xml" 2>/dev/null && GROK=1
  if [ "$GROK" -eq 1 ] && [ "${IDLE:-0}" -ge "$MIN_IDLE" ]; then
    if bash "$B/tools/agent_should_wire.sh" 2>/dev/null; then
      PROMPT=$(cat "$B/reports/SANITIZED_PROMPT.md" 2>/dev/null || true)
      if [ -n "$PROMPT" ]; then
        bash "$B/tools/wire_send_ui.sh" "$PROMPT" >>"$B/reports/wire_send.log" 2>&1 || true
        bash "$B/tools/agent_consume_iteration.sh" >>"$B/reports/agent_consume.log" 2>&1 &
        [ -s "$B/queue/agent_task.txt" ] && : > "$B/queue/agent_task.txt" || true
      fi
    fi
  fi
  sleep "$POLL"
done
COLLAB
chmod +x "$B/tools/collab_rish_loop.sh"

cat > "$B/tools/broccoli_worker.sh" <<'WK'
#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
Q="$B/queue/pending.txt"
[ -s "$Q" ] || exit 0
LINE=$(head -1 "$Q")
sed -i '1d' "$Q" 2>/dev/null || true
eval "$LINE" >>"$B/reports/worker.log" 2>&1 || true
WK
chmod +x "$B/tools/broccoli_worker.sh"

cat > "$B/tools/broccoli-daemon.sh" <<'DM'
#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
echo "$(date -Iseconds) daemon start" >>"$B/reports/daemon.log"
bash "$B/tools/collab_rish_loop.sh" >>"$B/reports/collab.log" 2>&1 &
COLLAB_PID=$!
while true; do
  bash "$B/tools/broccoli_worker.sh" 2>/dev/null || true
  kill -0 "$COLLAB_PID" 2>/dev/null || { bash "$B/tools/collab_rish_loop.sh" >>"$B/reports/collab.log" 2>&1 & COLLAB_PID=$!; }
  sleep 30
done
DM
chmod +x "$B/tools/broccoli-daemon.sh"

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
df -h "$HOME" | tail -1
echo ALIVE_REINIT_OK
RI
chmod +x "$B/tools/reinit_agent.sh"

mkdir -p "$HOME/bin"
cat > "$HOME/bin/b" <<'BCLI'
#!/data/data/com.termux/files/usr/bin/bash
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
B="$HOME/broccoli"
case "${1:-}" in
  reinit) bash "$B/tools/reinit_agent.sh" ;;
  status) df -h "$HOME"|tail -1; pgrep -af 'collab|broccoli-daemon|watchdog'||true; tail -5 "$B/reports/wire_send.log" 2>/dev/null;;
  wire-debug) bash "$B/lib/ui_dump_rish.sh"; python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml"; grep -o 'package="[^"]*"' "$B/reports/ui_dump.xml"|head -1;;
  wire-test) bash "$B/tools/wire_send_ui.sh" "${2:-Reply exactly: WIRE_OK}"; tail -8 "$B/reports/wire_send.log";;
  interject) printf '%s\n' "${2:-Broccoli online. What should we do next?}" > "$B/queue/agent_task.txt"; bash "$B/tools/write_sanitized_prompt.sh"; echo "queued — will wire when Grok+idle+composer ok";;
  agenda) printf '%s\n' "${2:-Advance Broccoli agenda.}" > "$B/queue/agent_task.txt"; bash "$B/tools/write_sanitized_prompt.sh";;
  alive) nohup bash "$B/tools/broccoli-daemon.sh" >>"$B/reports/daemon.log" 2>&1 & echo "daemon pid $!";;
  *) bash "$B/tools/b_cli.sh" "$@" 2>/dev/null || echo "b reinit|status|wire-debug|wire-test|interject|agenda|alive";;
esac
BCLI
chmod +x "$HOME/bin/b"
grep -q 'HOME/bin' ~/.bashrc 2>/dev/null || echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc

echo "PATCH_ALIVE_OK — run: export PATH=\$HOME/bin:\$PATH && b reinit"
