#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
ROOT="$HOME/broccoli"
export PATH="$ROOT/bin:$PATH"

while true; do
  clear
  echo "===== BROCC GROK LOOP $(date) ====="
  echo
  echo "[+] Checking foreground..."
  if python3 "$ROOT/modules/grok_focus.py"; then
    echo "[+] Grok detected"
    echo
    echo "[+] Probe"
    brocc probe || true
    echo
    echo "[+] Harvest"
    brocc harvest || true
  else
    echo "[!] Grok not foreground — waiting..."
  fi
  sleep 15
done
