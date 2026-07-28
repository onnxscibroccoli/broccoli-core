#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
CMD="${1:?}"
if command -v rish >/dev/null 2>&1; then exec rish -c "$CMD"; fi
[ -x ./rish.sh ] && exec ./rish.sh -c "$CMD"
[ -x ./rish_exec.sh ] && exec ./rish_exec.sh "$CMD"
echo FATAL_no_rish >&2; exit 127
