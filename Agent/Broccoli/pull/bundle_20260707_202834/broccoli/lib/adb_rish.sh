#!/data/data/com.termux/files/usr/bin/bash
# Retired archived launcher; source content below is preserved for provenance.
echo "RETIRED_PHYSICAL_RISH: use broccoli-core/lib/rish_run.sh" >&2
return 78 2>/dev/null || exit 78
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
bash "$HOME/aim_rish_ensure.sh" 2>/dev/null || true
printf '%s\n' "$@" | rish
