#!/usr/bin/env python3
import subprocess, sys
from pathlib import Path
H = Path.home()
def main():
    if len(sys.argv) > 1 and sys.argv[1] in ('wire', 'wire-only'):
        subprocess.check_call([sys.executable, str(H / 'broccoli/lib/brocc_wire.py')])
        return 0
    print('brocc-paste wire')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
