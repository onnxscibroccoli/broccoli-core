#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
CMD="$*"
[ -n "$CMD" ] || { echo "usage: rish_run.sh <shell-cmd>"; exit 2; }
rish -c "$CMD"
