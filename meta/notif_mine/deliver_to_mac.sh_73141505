#!/data/data/com.termux/files/usr/bin/bash
# After coordinator runs: clipboard + to_chat.md + notify (user pastes once to Mac OR reads to_chat)
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
BUNDLE="$HOME/broccoli/reports/DEVICE_OUTPUT_FOR_MAC.txt"
[ -s "$BUNDLE" ] || bash "$HOME/broccoli/tools/prepare_mac_bundle.sh" >/dev/null
BODY="$(head -c 3500 "$BUNDLE")"
{
  echo ""
  echo "--- DEVICE_OUTPUT $(date -Iseconds) ---"
  cat "$BUNDLE"
  echo "---"
} >> "$HOME/broccoli/thread/to_chat.md"
termux-clipboard-set <<< "$BODY" 2>/dev/null || true
command -v termux-notification >/dev/null 2>&1 && \
  termux-notification --id broccoli_deliver --title "Broccoli → Mac" \
    --content "DEVICE_OUTPUT on clipboard + to_chat.md (paste to Mac Grok)" --priority high 2>/dev/null || true
echo "delivered bytes=$(wc -c < "$BUNDLE") clipboard+to_chat"
