#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BROCCOLI_DIR="${BROCCOLI_DIR:-$HOME/broccoli}"
FAIL=0
pass() { echo "PASS: $1"; }
fail() { echo "FAIL: $1"; FAIL=$((FAIL+1)); }
[[ -d "$BROCCOLI_DIR" && -w "$BROCCOLI_DIR" ]] && pass dir_writable || fail dir_writable
[[ -x "$BROCCOLI_DIR/rish.sh" ]] && pass rish_wrapper || fail rish_wrapper
[[ -f "$BROCCOLI_DIR/broccoli_host.py" ]] && pass host_py || fail host_py
[[ -f "$BROCCOLI_DIR/chat_scraper.py" ]] && pass chat_scraper || fail chat_scraper
[[ -f "$BROCCOLI_DIR/chat_profile.json" ]] && pass chat_profile || fail chat_profile
python3 -c "import json; json.load(open('$BROCCOLI_DIR/chat_profile.json'))" 2>/dev/null && pass profile_json || fail profile_json
echo '{"t":1}' > "$BROCCOLI_DIR/.write_test" && rm -f "$BROCCOLI_DIR/.write_test" && pass state_rw || fail state_rw
bash "$BROCCOLI_DIR/ui.sh" 2>/dev/null; [[ -s "$BROCCOLI_DIR/window_dump.xml" ]] && pass ui_dump || fail ui_dump
python3 "$BROCCOLI_DIR/chat_scraper.py" --once >/dev/null 2>&1 && pass scrape_once || fail scrape_once
command -v termux-clipboard-get >/dev/null 2>&1 && pass termux_clipboard || fail termux_clipboard
[[ -x "$BROCCOLI_DIR/chat_copy_fetch.sh" ]] && pass copy_fetch_sh || fail copy_fetch_sh
if [[ -x "$BROCCOLI_DIR/rish.sh" ]]; then
  sh "$BROCCOLI_DIR/rish.sh" sh -c 'echo ok' 2>/dev/null | grep -q ok && pass rish_echo || fail rish_echo
fi
echo "FAIL=$FAIL" | tee "$BROCCOLI_DIR/self_test_results.txt"
exit "$FAIL"
