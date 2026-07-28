#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
python3 -c "
import json
from pathlib import Path
B=Path('$B')
s=json.loads((B/'state.json').read_text()) if (B/'state.json').is_file() else {}
l=(B/'learned_inject.json').is_file()
exit(0 if s.get('god_mode_learned') or l else 1)
"
