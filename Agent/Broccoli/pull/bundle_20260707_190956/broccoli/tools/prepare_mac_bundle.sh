#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
OUT="$HOME/broccoli/reports/DEVICE_OUTPUT_FOR_MAC.txt"
{
  echo "===== BROCCOLI DEVICE OUTPUT $(date -Iseconds) ====="
  echo "## DAEMONS"
  pgrep -af 'agent_daemon|heal_supervisor' 2>/dev/null || echo "(none)"
  echo ""
  echo "## QUEUE"
  cat "$HOME/broccoli/queue/pending.txt" 2>/dev/null || true
  echo ""
  echo "## AGENT_ITERATION"
  cat "$HOME/broccoli/meta/agent_iteration.json" 2>/dev/null || true
  echo ""
  echo "## INVENTORY (head)"
  head -120 "$HOME/broccoli/reports/INVENTORY_REPORT.md" 2>/dev/null || echo "(run inventory first)"
  echo ""
  echo "## INVESTIGATION (head)"
  head -80 "$HOME/broccoli/reports/INVESTIGATION_REPORT.md" 2>/dev/null || true
  echo ""
  echo "## WIRE_LOG (tail)"
  tail -15 "$HOME/broccoli/reports/wire_send.log" 2>/dev/null || true
  echo "===== END ====="
} > "$OUT"
wc -c < "$OUT"
