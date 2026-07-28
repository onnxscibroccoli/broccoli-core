# Broccoli full implementation run
- Time: Mon Jul 13 01:37:53 EDT 2026
- ROOT: /data/data/com.termux/files/home/broccoli
- apply-cache: 0

## 1. Launch path
### bin/brocc
```
#!/data/data/com.termux/files/usr/bin/bash
export BRO="${BRO:-$HOME/broccoli}"
export PATH="$PREFIX/bin:$PATH"
export PYTHONPATH="$BRO/lib"
export BROCCOLI_NO_ENTER=1 BROCCOLI_SEND_MODE=sibling_only
REAL=""
for c in "$PREFIX/bin/brocc" "$HOME/.local/bin/brocc"; do
  [[ -x "$c" && "$c" != "$BRO/bin/brocc" ]] && REAL="$c" && break
done
if [[ -n "$REAL" ]]; then exec "$REAL" "$@"; fi
case "${1:-}" in
  wire|loop|start) shift; exec "$BRO/bin/wire" "$@" ;;
  agent-loop-once)
    python3 -c "
import os,sys,json
sys.path.insert(0,'$BRO/lib')
os.environ['BROCCOLI_NO_ENTER']='1'
os.environ['BROCCOLI_SEND_MODE']='sibling_only'
from broccoli_core_round import full_round
from pathlib import Path
t=Path('$BRO/inbox/prompt.txt').read_text(encoding='utf-8',errors='replace').strip() or 'BROCC_TASK reply exactly: LOOP_OK'
print(json.dumps(full_round(t),indent=2))
"
    exit 0 ;;
  doctor) python3 "$BRO/tools/bin_research.py" 2>/dev/null | tail -5 ;;
  *) echo "brocc-shim: use $BRO/bin/wire or install real brocc in PREFIX"; exit 1 ;;
esac
```
### bin/wire
```
#!/data/data/com.termux/files/usr/bin/bash
export BRO=~/broccoli
export PATH="$PREFIX/bin:$BRO/bin:$BRO/tools:$PATH"
pkill -9 -f broccoli_infinite_dev_loop 2>/dev/null || true
sleep 1
if pgrep -f broccoli_infinite_dev_loop.py >/dev/null; then
  echo "wire: loop already up"
  pgrep -af broccoli_infinite_dev_loop
  exit 0
fi
python3 "$BRO/tools/search_notif_codebase.py" | tail -30
nohup "$BRO/tools/run_infinite.sh" >>"$BRO/reports/infinite_nohup.log" 2>&1 &
sleep 2
pgrep -af broccoli_infinite_dev_loop || tail -15 "$BRO/reports/infinite_nohup.log"
```
### boot/reboot_first_job.sh
```
#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$HOME/broccoli/reports/reboot_first.log"
mkdir -p "$(dirname "$LOG")"
exec >>"$LOG" 2>&1
echo "=== codevel_reinit $(date -Iseconds) ==="
am start -n com.termux/com.termux.app.TermuxActivity 2>/dev/null || true
sleep 1
[ -x "$HOME/aim_rish_ensure.sh" ] && bash "$HOME/aim_rish_ensure.sh" || true
printf 'id\n' | rish 2>/dev/null | head -3 || true
echo "CODEVEL_OK $(date -Iseconds)" > "$HOME/broccoli/LAST_RUN.txt"
printf '%s\n' 'ASK|Reply with one word: PONG' > "$HOME/broccoli/queue/pending.txt"
[ -x "$HOME/broccoli/tools/brocc_loop.sh" ] && pkill -f brocc_loop.sh 2>/dev/null || true
[ -x "$HOME/broccoli/tools/brocc_loop.sh" ] && nohup bash "$HOME/broccoli/tools/brocc_loop.sh" >>"$HOME/broccoli/reports/loop.log" 2>&1 &
echo "=== codevel_reinit end ==="
```
### termux boot
```
total 11
drwx------. 2 u0_a347 u0_a347 3452 Jul  7 18:49 .
drwx------. 3 u0_a347 u0_a347 3452 Jul  6 21:39 ..
lrwxrwxrwx. 1 u0_a347 u0_a347   66 Jul  6 21:48 00-broccoli-first.sh -> /data/data/com.termux/files/home/broccoli/boot/reboot_first_job.sh
-rwxr-xr-x. 1 u0_a347 u0_a347  457 Jul  7 18:49 broccoli-codev-loop.sh
```
### grep call graph
```
/data/data/com.termux/files/home/broccoli/bin/brocc:19:from broccoli_core_round import full_round
/data/data/com.termux/files/home/broccoli/lib/agent_loop.py:16:LOG = REP / "agent_loop.jsonl"
/data/data/com.termux/files/home/broccoli/lib/brocc_wire.py:4:CL = LIB / "closed_loop.py"
/data/data/com.termux/files/home/broccoli/lib/brocc_wire.py:6:    print("no closed_loop")
/data/data/com.termux/files/home/broccoli/lib/brocc_wire.py:9:if "catalog_loop_hook" in s:
/data/data/com.termux/files/home/broccoli/lib/brocc_wire.py:12:inj = "\nimport sys\nfrom pathlib import Path as _P\nsys.path.insert(0, str(_P.home() / \"broccoli\" / \"lib\"))\nfrom catalog_loop_hook import enrich_outgoing, maybe_catalog, is_catalog_ok\n"
/data/data/com.termux/files/home/broccoli/lib/brocc_wire.py:23:print("PATCH closed_loop ok")
/data/data/com.termux/files/home/broccoli/lib/broccoli_operator.py:13:PIDF = REP / "agent_loop.pid"
/data/data/com.termux/files/home/broccoli/lib/broccoli_operator.py:58:            [sys.executable, str(LIB / "agent_loop.py")],
/data/data/com.termux/files/home/broccoli/lib/broccoli_operator.py:117:            "broccoli_agent_loop_v1",
/data/data/com.termux/files/home/broccoli/lib/broccoli_rish_ui.py:132:    from broccoli_core_round import full_round
/data/data/com.termux/files/home/broccoli/lib/closed_loop.py:2:from catalog_loop_hook import enrich_outgoing, maybe_catalog, is_catalog_ok
/data/data/com.termux/files/home/broccoli/lib/closed_loop.py:22:DB = INBOX / "closed_loop.db"
/data/data/com.termux/files/home/broccoli/lib/closed_loop.py:24:LOG = BRO / "reports" / "closed_loop.log"
/data/data/com.termux/files/home/broccoli/lib/closed_loop.py:25:STATE = INBOX / "closed_loop_state.json"
/data/data/com.termux/files/home/broccoli/lib/closed_loop.py:214:    print("usage: closed_loop.py run|once|recv|send <text>")
/data/data/com.termux/files/home/broccoli/lib/paste_accommodate.py:7:        subprocess.check_call([sys.executable, str(H / 'broccoli/lib/brocc_wire.py')])
```

## 2. Wire diagnose
```
-rw-------. 1 u0_a347 u0_a347 0 Jul  7 22:58 /data/data/com.termux/files/home/broccoli/state/infinite.lock
/data/data/com.termux/files/home/broccoli/meta/inbox/from_mac/:
total 7
drwx------. 2 u0_a347 u0_a347 3452 Jul  7 16:40 .
drwx------. 4 u0_a347 u0_a347 3452 Jul  7 16:40 ..

/data/data/com.termux/files/home/broccoli/meta/inbox/to_mac/:
total 11
drwx------. 2 u0_a347 u0_a347 3452 Jul  7 16:53 .
drwx------. 4 u0_a347 u0_a347 3452 Jul  7 16:40 ..
-rw-------. 1 u0_a347 u0_a347  460 Jul  7 17:55 loop_packet.json
--- loop_packet.json ---
{
  "role": "brocc",
  "ts": "2026-07-07 17:55:02",
  "phase": "await_grok",
  "summary": {
    "missing": 1,
    "stale": 7,
    "ok": 568
  },
  "ask_grok": "Reply with grok_commands.sh lines only (brocc/python3). Mac: adb push to inbox/from_mac/grok_commands.sh",
  "mac_pull": [
    "adb pull /sdcard/Broccoli/mirror_manifest.json .",
    "adb pull /sdcard/Broccoli/mirror ./Broccoli-mirror",
    "adb pull /sdcard/Broccoli/pull/CLIPBOARD_LAST.txt ."
  ]
}--- mac ---
  0 /data/data/com.termux/files/home/broccoli/mac/inbox.jsonl
135 /data/data/com.termux/files/home/broccoli/mac/processed.jsonl
135 total
{"type":"grok","attach_context":true,"body":"LOOP_OK line1. NEXT_STEP: one line. Given AGENT_CONTEXT, suggest one cal fix if needed."}
--- ui loop ---
Continue until TASK_COMPLETE. UI verdict: not done yet.
Reasons: quarry:has_fail
Previous output:

Test:

Reply with fix as one code block, or ITER_OK / TASK_COMPLETE when done.--- freshness ---
-rw-------. 1 u0_a347 u0_a347    240 Jul 11 13:33 /data/data/com.termux/files/home/broccoli/inbox/grok_reply.txt
-rw-------. 1 u0_a347 u0_a347    143 Jul 10 03:07 /data/data/com.termux/files/home/broccoli/inbox/prompt.txt
-rw-------. 1 u0_a347 u0_a347    422 Jul 11 13:31 /data/data/com.termux/files/home/broccoli/thread/grok_last.txt
-rw-------. 1 u0_a347 u0_a347 151689 Jul 12 16:41 /data/data/com.termux/files/home/broccoli/ui/latest.xml
--- brocc_wire refs ---
```
If grok_reply + latest.xml are fresh but from_mac empty → Mac must write meta/inbox/from_mac/.

## 3. Disk
```
1.5G	/data/data/com.termux/files/home/broccoli/quarantine/dupes
cache files: 0
```

## 4. Cache trim
```
(no meta/cache)
```
_Dry-run. Run: bash broccoli_full_impl.sh --apply-cache_

## 5. Helpers installed
- /data/data/com.termux/files/home/broccoli/scripts/map_launch_path.sh
- /data/data/com.termux/files/home/broccoli/scripts/diagnose_wire.sh
- /data/data/com.termux/files/home/broccoli/scripts/trim_meta_cache.sh

## 6. Next
1. Mac → phone: populate meta/inbox/from_mac/
2. Phone loop: cd /data/data/com.termux/files/home/broccoli && ./bin/brocc  (or wire)
3. Optional: rm -rf quarantine/dupes after backup (~1.2GB)
