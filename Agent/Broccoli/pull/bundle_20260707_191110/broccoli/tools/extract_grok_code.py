#!/usr/bin/env python3
import re
from pathlib import Path
HOME = Path.home()
SRC = HOME / "broccoli/thread/grok_last.txt"
OUT = HOME / "broccoli/sandbox/from_grok"
OUT.mkdir(parents=True, exist_ok=True)
text = SRC.read_text(errors="replace") if SRC.is_file() else ""
blocks = re.findall(r"```(?:bash|sh)?\s*\n(.*?)```", text, re.S)
if not blocks:
    blocks = re.findall(r"```\s*\n(.*?)```", text, re.S)
for i, b in enumerate(blocks[:5]):
    p = OUT / f"block_{i}.sh"
    p.write_text("#!/data/data/com.termux/files/usr/bin/bash\nset -eu\n" + b.strip() + "\n", encoding="utf-8")
    p.chmod(0o755)
    print("wrote", p)
