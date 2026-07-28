#!/data/data/com.termux/files/usr/bin/bash
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
B="$HOME/broccoli"
case "${1:-}" in
  reinit)
    pkill -f collab_rish_loop 2>/dev/null || true
    pkill -f broccoli-daemon 2>/dev/null || true
    sleep 1
    nohup bash "$B/tools/broccoli-daemon.sh" >>"$B/reports/daemon.log" 2>&1 &
    echo "daemon $!"
    ;;
  status) pgrep -af 'collab|broccoli-daemon' || echo "no daemon"; df -h "$HOME" | tail -1 ;;
  wire-test) bash "$B/tools/wire_send_ui.sh" "${2:-Reply: WIRE_OK}"; tail -6 "$B/reports/wire_send.log" ;;
  interject)
    shift
    printf '%s' "$*" | head -c 3800 > "$B/queue/agent_task.txt"
    echo "queued $(wc -c < "$B/queue/agent_task.txt") bytes"
    ;;
  diag) bash "$B/tools/wire_diag.sh" ;;
  smoke) bash "$B/tools/smoke_boot.sh" ;;
  *)
    echo "b reinit | status | wire-test | interject | diag | smoke"
    ;;
esac
