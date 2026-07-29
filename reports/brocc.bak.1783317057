#!/data/data/com.termux/files/usr/bin/bash
ROOT="$HOME/broccoli"
case "${1:-}" in
start)
  if [ -f "$ROOT/daemon.pid" ] && kill -0 "$(cat "$ROOT/daemon.pid")" 2>/dev/null; then echo RUNNING "$(cat "$ROOT/daemon.pid")"; exit 0; fi
  nohup "$HOME/broccoli-daemon.sh" >> "$ROOT/daemon.log" 2>&1 & echo started $! ;;
stop) [ -f "$ROOT/daemon.pid" ] && kill "$(cat "$ROOT/daemon.pid")" 2>/dev/null; rm -f "$ROOT/daemon.pid" ;;
status)
  [ -f "$ROOT/daemon.pid" ] && kill -0 "$(cat "$ROOT/daemon.pid")" 2>/dev/null && echo RUNNING "$(cat "$ROOT/daemon.pid")" || echo STOPPED
  ls "$ROOT/inbox/grok" 2>/dev/null; cat "$ROOT/LAST_RUN.txt" 2>/dev/null ;;
task) python3 "$HOME/broccoli_task.py" "${2:-status}" "${3:-}" ;;
inject) shift; echo "$*" > "$ROOT/user/PENDING.md"; termux-toast -s "user inject" 2>/dev/null; echo ok ;;
pause) python3 -c "import json;from pathlib import Path as P;p=P.home()/'broccoli/tasks/state.json';d=json.loads(p.read_text()) if p.is_file() else {};d['status']='PAUSED';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d))"; termux-toast -s PAUSED 2>/dev/null ;;
resume) python3 -c "import json;from pathlib import Path as P;p=P.home()/'broccoli/tasks/state.json';d=json.loads(p.read_text()) if p.is_file() else {};d['status']='RUNNING';p.write_text(json.dumps(d))"; termux-toast -s RUNNING 2>/dev/null ;;
log) tail -n "${2:-50}" "$ROOT/daemon.log" ;;
report) cat "$ROOT/reports/latest.txt"; termux-clipboard-set < "$ROOT/reports/latest.txt" 2>/dev/null ;;
ask) p="${2:-grok}"; shift 2; f="$ROOT/inbox/$p/$(date +%s).txt"; printf '%s\n' "$*" > "$f"; echo queued "$f" ;;

research)
  sub="${2:-doctor}"
  shift 2 2>/dev/null || shift 1
  case "$sub" in
    doctor) python3 "$HOME/broccoli_research.py" doctor ;;
    round) python3 "$HOME/broccoli_research.py" round "$*" ;;
    google) python3 "$HOME/broccoli_research.py" enqueue-google "$*" ;;
    grok) python3 "$HOME/broccoli_research.py" enqueue-grok "$*" ;;
    *) python3 "$HOME/broccoli_research.py" "$sub" "$@" ;;
  
meta-heal|auto-heal)
  exec python3 "$HOME/broccoli/broccoli_meta_heal.py"
  ;;
esac ;;

user-wait)
  python3 "$HOME/broccoli_user_wait.py" wait "$*" ;;
user-done)
  python3 "$HOME/broccoli_user_wait.py" done "$*"
  brocc focus 2>/dev/null || true ;;
run-once) "$HOME/broccoli_worker.sh" ;;
research) python3 "$HOME/broccoli_research.py" doctor ;;
*) echo "brocc start|stop|status|task|inject|pause|resume|user-wait|user-done|log|report|ask|run-once" ;;
esac
# delegate extended commands
case "$1" in
  secondary|secondary-ready|secondary-on|google-secondary-test|pack|godmode)
    exec "$HOME/brocc-extras" "$@"
    ;;
esac

