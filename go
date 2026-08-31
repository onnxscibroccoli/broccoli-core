#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
B="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
D="${BROCCOLI_DIR:-$HOME/broccoli}"
export BROCCOLI_DIR="$D"
cmd="${1:-}"
case "$cmd" in
  loop)
    python3 "$D/broccoli_chat_loop.py" "${@:2}"
    ;;
  daemon)
    nohup python3 "$D/broccoli_chat_loop.py" "${@:2}" >>"$D/chat_loop.log" 2>&1 &
    echo $! >"$D/loop.pid"
    echo "daemon pid $(cat "$D/loop.pid")"
    ;;
  stop)
    kill "$(cat "$D/loop.pid" 2>/dev/null)" 2>/dev/null && rm -f "$D/loop.pid" && echo stopped || echo no pid
    ;;
  calibrate)
    bash "$D/chat_calibrate.sh"
    ;;
  launch)
    bash "$D/grok_launch.sh"
    ;;
  launch-grok|launch_grok)
    if [[ -x "$B/brocc" ]]; then
      exec "$B/brocc" launch-grok "${@:2}"
    elif [[ -x "$B/bin/brocc" ]]; then
      exec "$B/bin/brocc" launch-grok "${@:2}"
    else
      echo "go: brocc not found (tried $B/brocc and $B/bin/brocc)" >&2
      exit 127
    fi
    ;;
  *)
    echo "usage: go loop|daemon|stop|calibrate|launch|launch-grok"
    exit 1
    ;;
esac
