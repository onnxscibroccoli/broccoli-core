#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
# shellcheck source=/dev/null
source "$B/meta/wire_coords.env"
sleep "${CONSUME_WAIT_SEC:-3}"
bash "$B/lib/ui_dump_rish.sh" 2>/dev/null || true
bash "$B/tools/consume_response.sh" 2>/dev/null || true
