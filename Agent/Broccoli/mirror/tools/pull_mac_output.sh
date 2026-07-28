#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
rm -f "$HOME/broccoli/meta/wire_inflight"
python3 -c "
import json
from pathlib import Path
p=Path.home()/'broccoli/meta/agent_iteration.json'
d=json.loads(p.read_text()) if p.is_file() else {}
d['status']='idle'
p.write_text(json.dumps(d,indent=2))
" 2>/dev/null || true
[ -f "$HOME/broccoli/tools/inventory_md_tasks.py" ] && python3 "$HOME/broccoli/tools/inventory_md_tasks.py" >/dev/null 2>&1 || true
bash "$HOME/broccoli/tools/prepare_mac_bundle.sh" 2>/dev/null || {
  OUT="$HOME/broccoli/reports/DEVICE_OUTPUT_FOR_MAC.txt"
  { echo "===== DEVICE $(date -Iseconds) ====="
    pgrep -af 'agent_daemon|heal_supervisor' || true
    echo "## QUEUE"; cat "$HOME/broccoli/queue/pending.txt" 2>/dev/null || true
    echo "## ITER"; cat "$HOME/broccoli/meta/agent_iteration.json" 2>/dev/null || true
    echo "## WIRE"; tail -12 "$HOME/broccoli/reports/wire_send.log" 2>/dev/null || true
    echo "===== END ====="
  } > "$OUT"
}
bash "$HOME/broccoli/tools/deliver_to_mac.sh" 2>/dev/null || {
  B="$HOME/broccoli/reports/DEVICE_OUTPUT_FOR_MAC.txt"
  termux-clipboard-set < "$B" 2>/dev/null || cat "$B"
}
bash "$HOME/broccoli/tools/go_install.sh" 2>/dev/null || true
echo "===== PASTE TO MAC GROK ====="
head -c 4000 "$HOME/broccoli/reports/DEVICE_OUTPUT_FOR_MAC.txt"
echo ""
echo "===== END (also clipboard + tail to_chat.md) ====="
