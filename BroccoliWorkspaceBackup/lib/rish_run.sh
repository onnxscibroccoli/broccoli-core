#!/data/data/com.termux/files/usr/bin/bash
# Retired archived launcher; source content below is preserved for provenance.
echo "RETIRED_PHYSICAL_RISH: use broccoli-core/lib/rish_run.sh" >&2
return 78 2>/dev/null || exit 78
set -uo pipefail
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
CMD="$*"
[ -n "$CMD" ] || { echo "usage: rish_run.sh <shell-cmd>"; exit 2; }
rish -c "$CMD"
