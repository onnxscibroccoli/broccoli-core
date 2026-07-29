#!/data/data/com.termux/files/usr/bin/bash
export BRO=~/broccoli PYTHONPATH=$BRO/lib RISH_APPLICATION_ID=com.termux BROCCOLI_GROK_PKG=ai.x.grok
python3 <<'PY'
import json, sys
sys.path.insert(0, "$BRO/lib")
from broccoli_rish_shell import shell
from broccoli_adb_ui import dump_xml, parse_tree, find_composer, find_send_adb
GROK="ai.x.grok"
shell(f"monkey -p {GROK} -c android.intent.category.LAUNCHER 1")
import time; time.sleep(0.6)
xml = dump_xml()
print("dump_bytes", len(xml))
_, parent, nodes = parse_tree(xml)
comp = find_composer(nodes)
comp_el = comp["el"] if comp else None
send = find_send_adb(nodes, parent, comp_el, comp)
print(json.dumps({"composer": {k: comp[k] for k in ("cx","cy","x2","rid","desc")} if comp else None,
                  "send": send}, indent=2))
PY
