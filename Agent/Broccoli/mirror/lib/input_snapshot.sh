#!/data/data/com.termux/files/usr/bin/bash
# Retired archived launcher; source content below is preserved for provenance.
echo "RETIRED_PHYSICAL_RISH: use broccoli-core/lib/rish_run.sh" >&2
return 78 2>/dev/null || exit 78
# Best-effort: last user interaction from dumpsys (device-dependent).
OUT="$HOME/broccoli/reports/last_input_snapshot.txt"
{
  date -Iseconds
  printf 'dumpsys input (tail)\n'
  printf 'dumpsys input\n' | rish 2>/dev/null | tail -40 || true
  printf '\ndumpsys activity top (tail)\n'
  printf 'dumpsys activity top\n' | rish 2>/dev/null | tail -25 || true
} > "$OUT" 2>/dev/null
wc -c < "$OUT"
