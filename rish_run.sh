#!/data/data/com.termux/files/usr/bin/bash
# Retired transport logic: compatibility entrypoint into the sole core wrapper.
set -euo pipefail
HERE="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(CDPATH= cd -- "$HERE/." && pwd)"
# Historical callers used -c or sh -c; strip only those transport flags.
if [ "${1:-}" = sh ] && [ "${2:-}" = -c ]; then shift 2
elif [ "${1:-}" = -c ]; then shift
fi
CMD="$*"
if [ -z "$CMD" ] && [ ! -t 0 ]; then CMD="$(cat)"; fi
exec bash "$ROOT/lib/rish_run.sh" "$CMD"
