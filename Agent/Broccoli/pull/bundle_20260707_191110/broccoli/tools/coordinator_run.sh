#!/data/data/com.termux/files/usr/bin/bash
# Usage: coordinator_run.sh inventory|status|full
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
CMD="${1:-full}"
case "$CMD" in
  inventory) bash "$HOME/broccoli/tools/inventory_md_tasks.sh" ;;
  status)
    bash "$HOME/broccoli/tools/inventory_md_tasks.sh" >/dev/null 2>&1 || true
    bash "$HOME/broccoli/tools/prepare_mac_bundle.sh"
    ;;
  full)
    bash "$HOME/broccoli/tools/inventory_md_tasks.sh" || true
    [ -x "$HOME/broccoli/tools/investigate_system.sh" ] && bash "$HOME/broccoli/tools/investigate_system.sh" --no-live >>"$HOME/broccoli/reports/inventory.log" 2>&1 || true
    bash "$HOME/broccoli/tools/prepare_mac_bundle.sh"
    bash "$HOME/broccoli/tools/deliver_to_mac.sh"
    ;;
  *) echo "usage: inventory|status|full"; exit 1 ;;
esac
bash "$HOME/broccoli/tools/go_install.sh" 2>/dev/null || true
