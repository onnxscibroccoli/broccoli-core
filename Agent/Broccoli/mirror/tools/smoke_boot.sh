#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
RISH=$(command -v rish); CLIP=$(command -v termux-clipboard-set)
DIAG=$(bash "$B/tools/wire_diag.sh" 2>/dev/null || echo '{}')
OK_PARSE=$(echo "$DIAG" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('parse',{}).get('ok'))" 2>/dev/null || echo False)
WIRE=skip
if [ "$OK_PARSE" = "True" ]; then
  bash "$B/tools/wire_send_ui.sh" "SMOKE: $(date +%H%M%S)" >>"$B/reports/wire_send.log" 2>&1 && WIRE=pass || WIRE=fail
else
  WIRE=skip_no_grok
fi
python3 - "$RISH" "$CLIP" "$DIAG" "$WIRE" <<'IN'
import json, sys, time
from pathlib import Path
rish, clip, diag_s, wire = sys.argv[1:5]
try: diag = json.loads(diag_s)
except: diag = {}
all_pass = bool(rish and clip and diag.get("dump_ok") and diag.get("parse",{}).get("ok") and wire == "pass")
out = {"ts": time.time(), "rish": rish, "clipboard": clip, "wire": wire, "diag": diag, "all_pass": all_pass}
Path.home().joinpath("broccoli/reports/smoke_report.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
IN
