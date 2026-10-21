#!/data/data/com.termux/files/usr/bin/bash
# Retired archived launcher; source content below is preserved for provenance.
echo "RETIRED_PHYSICAL_RISH: use broccoli-core/lib/rish_run.sh" >&2
return 78 2>/dev/null || exit 78
# Rish: one shell line per docs — stdin to rish, no bogus am intents.
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LINE="${*:-}"
if [ -z "$LINE" ] && [ ! -t 0 ]; then LINE="$(cat)"; fi
printf '%s\n' "$LINE" | rish
