#!/data/data/com.termux/files/usr/bin/bash
set -eu
if [ -z "${RUTO_COMMAND:-}" ]; then
  echo "RUTO_NOT_CONFIGURED: set RUTO_COMMAND to the reviewed RUTO bridge" >&2
  exit 78
fi
exec /data/data/com.termux/files/usr/bin/bash -lc "$RUTO_COMMAND"
