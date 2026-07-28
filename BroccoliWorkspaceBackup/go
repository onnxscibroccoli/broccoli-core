#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
D="${BROCCOLI_DIR:-$HOME/broccoli}"
export BROCCOLI_DIR="$D"
cmd="${1:-}"
case "$cmd" in
  loop)    python3 "$D/broccoli_chat_loop.py" "${@:2}" ;;
  daemon)  nohup python3 "$D/broccoli_chat_loop.py" "${@:2}" >>"$D/chat_loop.log" 2>&1 & echo $! >"$D/loop.pid"; echo "daemon pid $(cat "$D/loop.pid")" ;;
  stop)    kill "$(cat "$D/loop.pid" 2>/dev/null)" 2>/dev/null && rm -f "$D/loop.pid" && echo stopped || echo no pid ;;
  calibrate) bash "$D/chat_calibrate.sh" ;;
  launch)  bash "$D/grok_launch.sh" ;;
  *) echo "usage: go loop|daemon|stop|calibrate|launch"; exit 1 ;;
esac

launch-grok|launch_grok)
  exec "$B/brocc" launch-grok "$@"
  ;;
