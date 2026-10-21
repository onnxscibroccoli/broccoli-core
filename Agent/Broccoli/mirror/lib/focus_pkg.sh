#!/data/data/com.termux/files/usr/bin/bash
# Retired archived launcher; source content below is preserved for provenance.
echo "RETIRED_PHYSICAL_RISH: use broccoli-core/lib/rish_run.sh" >&2
return 78 2>/dev/null || exit 78
PKG="${1:-ai.x.grok}"
RAW="$(printf 'dumpsys activity activities\n' | rish 2>/dev/null || true)"
echo "$RAW" | grep -iE 'topResumedActivity|mResumedActivity' | head -2
echo "$RAW" | grep -q "$PKG" && exit 0 || exit 1
