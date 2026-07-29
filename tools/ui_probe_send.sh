#!/data/data/com.termux/files/usr/bin/bash
export BRO="${BRO:-$HOME/broccoli}"
export PYTHONPATH="$BRO/lib"
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
python3 -c "
import sys, time, json
sys.path.insert(0, '$BRO/lib')
from broccoli_agentic_chat import open_grok
from broccoli_ui_dump import ui_dump, nodes, dump_debug_summary
open_grok()
time.sleep(0.5)
print(json.dumps(dump_debug_summary(nodes(ui_dump())), indent=2))
"
