#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
export BRO="${BRO:-$HOME/broccoli}"
export PYTHONPATH="$BRO/lib"
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
python3 -c "
import json, sys
sys.path.insert(0, '$BRO/lib')
from broccoli_a11y_rish import a11y_status, open_accessibility_settings
print(json.dumps(a11y_status(), indent=2))
st = a11y_status()
if not st['installed']:
    print('INSTALL: build/install $BRO/a11y-apk (see README_A11Y.txt)')
if st['installed'] and not st['enabled']:
    print('ENABLE: opening Accessibility settings — turn ON Broccoli A11y Helper')
    open_accessibility_settings()
"
