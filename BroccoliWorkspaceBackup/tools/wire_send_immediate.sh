#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
B="$HOME/broccoli"
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
source "$B/meta/wire_coords.env" 2>/dev/null || true
PKG="${GROK_PKG:-com.ai.x.grok}"
MSG="${1:?msg}"
LOG="$B/reports/agent_loop.log"
XML="$B/reports/ui_dump.xml"
MARK="$(echo "$MSG" | head -c 48)"
log(){ echo "$(date -Iseconds) $*" >>"$LOG"; }
rish -c "am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p $PKG" >/dev/null 2>&1 || true
sleep 0.35
rish -c uiautomator dump /data/local/tmp/broccoli_ui.xml >/dev/null 2>&1 || true
rish -c cat /data/local/tmp/broccoli_ui.xml >"$XML" 2>/dev/null || true
[ -s "$XML" ] || { log FAIL dump_empty; exit 1; }
log OK dump_bytes=$(wc -c <"$XML")
printf '%s' "$MSG" | termux-clipboard-set
rish -c "input tap ${COMPOSER_X:-540} ${COMPOSER_Y:-2180}"; sleep 0.15
rish -c "input keyevent 279"; sleep 0.2
rish -c "input tap ${SEND_X:-980} ${SEND_Y:-2180}"; sleep 0.25
rish -c "input tap ${SEND_X:-980} ${SEND_Y:-2180}"; sleep 0.4
rish -c uiautomator dump /data/local/tmp/broccoli_ui.xml >/dev/null 2>&1 || true
rish -c cat /data/local/tmp/broccoli_ui.xml >"$XML" 2>/dev/null || true
if grep -qF "$MARK" "$XML" 2>/dev/null; then log OK sent_verified mark="$MARK"; exit 0; fi
rish -c "input keyevent 66"; sleep 0.35
rish -c uiautomator dump /data/local/tmp/broccoli_ui.xml >/dev/null 2>&1 || true
rish -c cat /data/local/tmp/broccoli_ui.xml >"$XML" 2>/dev/null || true
grep -qF "$MARK" "$XML" 2>/dev/null && { log OK sent_verified_enter mark="$MARK"; exit 0; }
log FAIL send_not_in_dump mark="$MARK"
exit 1
