#!/data/data/com.termux/files/usr/bin/bash
# Best-effort: last user interaction from dumpsys (device-dependent).
OUT="$HOME/broccoli/reports/last_input_snapshot.txt"
{
  date -Iseconds
  printf 'dumpsys input (tail)\n'
  printf 'dumpsys input\n' | bash /data/data/com.termux/files/home/broccoli-core/lib/rish_shell.sh 2>/dev/null | tail -40 || true
  printf '\ndumpsys activity top (tail)\n'
  printf 'dumpsys activity top\n' | bash /data/data/com.termux/files/home/broccoli-core/lib/rish_shell.sh 2>/dev/null | tail -25 || true
} > "$OUT" 2>/dev/null
wc -c < "$OUT"
