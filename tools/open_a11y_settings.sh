#!/data/data/com.termux/files/usr/bin/bash
export PYTHONPATH="${BRO:-$HOME/broccoli}/lib"
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
python3 -c "
import sys; sys.path.insert(0,'${BRO:-$HOME/broccoli}/lib')
from broccoli_a11y_rish import open_accessibility_settings, a11y_status
import json
print(json.dumps(a11y_status(), indent=2))
open_accessibility_settings()
"
