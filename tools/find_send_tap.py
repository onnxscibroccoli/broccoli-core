#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path
p = Path.home() / "broccoli/meta/send_pick.txt"
if p.is_file():
    a = p.read_text().split()
    if len(a) >= 2:
        x,y=int(a[0]),int(a[1])
        subprocess.run(["bash","-c",f'printf "input tap {x} {y}\\n" | bash /data/data/com.termux/files/home/broccoli-core/lib/rish_shell.sh'], check=False)
        print(json.dumps({"tap":[x,y],"why":"send_pick"}))
        sys.exit(0)
print(json.dumps({"err":"no_pick"})); sys.exit(2)
