#!/data/data/com.termux/files/usr/bin/bash
export BRO=~/broccoli PYTHONPATH=$BRO/lib BROCCOLI_GROK_PKG=ai.x.grok
echo "=== notif mine index ==="
cat "$BRO/meta/notif_mine_index.json" 2>/dev/null | head -40
echo "=== termux-notification-list (Grok filter) ==="
python3 -c "
import json,sys;sys.path.insert(0,'$BRO/lib')
from broccoli_notif import grok_notification_texts, list_notifications, has_termux_api
print('api',has_termux_api(),'total',len(list_notifications()))
for x in grok_notification_texts()[-5:]:
    print(x)
"
