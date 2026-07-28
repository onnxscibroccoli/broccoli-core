#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$(dirname "$0")"
PKG="${GROK_PKG:-ai.x.grok}"
on_grok() {
  python3 screen_state.py 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('1' if d.get('on_grok') or d.get('fg_package')=='$PKG' else '0')
" 2>/dev/null | grep -q 1
}
echo "[launch] grok_launch.sh first"
if [ -x grok_launch.sh ]; then
  timeout 22 bash grok_launch.sh 2>&1 | tail -3 || true
  for _ in $(seq 1 10); do sleep 1; on_grok && { echo ok=grok_launch.sh; bash ui_snapshot.sh 2>/dev/null; exit 0; }; done
fi
echo "[launch] FAIL fg=$(python3 screen_state.py 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin).get(\"fg_package\",\"\"))' 2>/dev/null)"
exit 1
