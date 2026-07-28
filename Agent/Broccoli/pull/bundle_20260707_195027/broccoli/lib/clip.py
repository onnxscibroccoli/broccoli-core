#!/usr/bin/env python3
import subprocess, sys
def set_text(s):
    p = subprocess.run(["termux-clipboard-set"], input=s.encode("utf-8", errors="replace"),
                       capture_output=True, timeout=15)
    return p.returncode == 0
def get_text():
    p = subprocess.run(["termux-clipboard-get"], capture_output=True, timeout=15)
    return p.stdout.decode("utf-8", errors="replace") if p.returncode == 0 else ""
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "get":
        print(get_text(), end="")
    else:
        set_text(sys.stdin.read())
