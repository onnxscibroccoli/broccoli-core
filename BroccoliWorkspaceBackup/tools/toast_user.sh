#!/data/data/com.termux/files/usr/bin/bash
# Retired archived launcher; source content below is preserved for provenance.
echo "RETIRED_PHYSICAL_RISH: use broccoli-core/lib/rish_run.sh" >&2
return 78 2>/dev/null || exit 78
set -eu
MSG="${1:-User input needed}"
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
termux-toast -s "$MSG" 2>/dev/null || true
printf 'cmd notification post -t "Broccoli" "co-dev" "%s"\n' "$MSG" | rish 2>/dev/null || true
printf 'am broadcast -a termux.toast --es text "%s" 2>/dev/null\n' "$MSG" | rish 2>/dev/null || true
echo "TOAST: $MSG"
