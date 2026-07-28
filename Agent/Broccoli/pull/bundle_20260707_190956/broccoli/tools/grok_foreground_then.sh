#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$HOME/broccoli/reports/foreground.log"
GROK_PKG=ai.x.grok
bash "$HOME/aim_rish_ensure.sh" 2>/dev/null || true
log(){ echo "$(date -Iseconds) $*" | tee -a "$LOG"; }
log "1 launch Grok native"
bash "$HOME/broccoli/lib/launch_grok_native.sh"
sleep 5
log "2 dump UI (rish)"
printf 'uiautomator dump --compressed /data/local/tmp/broccoli_ui.xml\nwc -c /data/local/tmp/broccoli_ui.xml\n' | rish 2>&1 | tail -3 | tee -a "$LOG"
cp -f /data/local/tmp/broccoli_ui.xml "$HOME/broccoli/ui/last_ui.xml" 2>/dev/null || true
PKG="$(grep -o 'package="[^"]*"' /data/local/tmp/broccoli_ui.xml 2>/dev/null | sort -u | head -5 | tr '\n' ' ')"
log "3 packages in dump: $PKG"
if ! grep -q 'ai.x.grok' /data/local/tmp/broccoli_ui.xml 2>/dev/null; then
  log "WARN Grok not in dump — tap Grok app on screen, wait 3s, re-dump"
  sleep 3
  printf 'uiautomator dump --compressed /data/local/tmp/broccoli_ui.xml\n' | rish
  cp -f /data/local/tmp/broccoli_ui.xml "$HOME/broccoli/ui/last_ui.xml" 2>/dev/null || true
fi
CMD="${1:-status}"
shift || true
case "$CMD" in
  status) wc -c "$HOME/broccoli/ui/last_ui.xml" 2>/dev/null; tail -5 "$LOG" ;;
  pong)
    log "4 send PONG"
    termux-clipboard-set <<< 'Reply with one word: PONG'
    GROK_PKG=ai.x.grok python3 "$HOME/broccoli/lib/grok_send_tap.py" 'Reply with one word: PONG' 2>&1 | tee -a "$LOG"
    sleep 8
    log "5 poll dump for reply"
    printf 'uiautomator dump --compressed /data/local/tmp/broccoli_ui.xml\n' | rish
    cp -f /data/local/tmp/broccoli_ui.xml "$HOME/broccoli/ui/last_ui.xml"
    grep -oi pong /data/local/tmp/broccoli_ui.xml | head -3 | tee -a "$LOG" || log "no PONG in xml yet"
    ;;
  ask)
    MSG="${*:-Reply with one word: PONG}"
    log "4 ask: $MSG"
    termux-clipboard-set <<< "$MSG"
    GROK_PKG=ai.x.grok python3 "$HOME/broccoli/lib/grok_send_tap.py" "$MSG" 2>&1 | tee -a "$LOG"
    sleep 10
    printf 'uiautomator dump --compressed /data/local/tmp/broccoli_ui.xml\n' | rish
    python3 "$HOME/broccoli/tools/extract_chat_from_xml.py" 2>/dev/null | tee -a "$LOG" || grep -i text= /data/local/tmp/broccoli_ui.xml | tail -8 | tee -a "$LOG"
    ;;
  paste-termux)
    log "Termux foreground — copy code block on PC/phone first"
    termux-clipboard-get
    ;;
esac
