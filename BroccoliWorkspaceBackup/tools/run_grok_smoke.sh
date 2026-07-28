#!/data/data/com.termux/files/usr/bin/bash
set -e
OUT="$HOME/broccoli/reports/smoke_last.txt"
mkdir -p "$HOME/broccoli/reports" "$HOME/broccoli/ui"
python3 "$HOME/broccoli_bootstrap.py" grok-smoke 2>&1 | tee "$OUT" || true
# if bootstrap wrote dump to stdout only, user may have ui dump in log - validate any saved xml
for f in "$HOME/broccoli/ui/last_ui.xml" "$HOME/broccoli/ui/last_capture.txt"; do
  if [[ -f "$f" ]] && grep -q GROK_SMOKE_OK "$f" 2>/dev/null; then
    echo "PASS GROK_SMOKE_OK (file $f)" | tee -a "$OUT"
    exit 0
  fi
done
if grep -q GROK_SMOKE_OK "$OUT" 2>/dev/null && grep -qE 'text="GROK_SMOKE_OK"|GROK_SMOKE_OK' "$OUT"; then
  echo "PASS GROK_SMOKE_OK (log)" | tee -a "$OUT"
  exit 0
fi
python3 "$HOME/broccoli/tools/grok_smoke_validate.py" "$HOME/broccoli/ui/last_ui.xml" 2>/dev/null && exit 0
echo "FAIL smoke" | tee -a "$OUT"
exit 1
