#!/usr/bin/env python3
"""UI dump via uiautomator (system path) + optional node tap by text."""
import subprocess, sys, re, json
from pathlib import Path

OUT = Path("/sdcard/Broccoli/ui/latest_a11y.xml")
OUT.parent.mkdir(parents=True, exist_ok=True)
TMP = "/sdcard/window_dump.xml"

def sh(cmd, t=30):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)

def dump():
    sh("shizuku -r sh -c 'uiautomator dump %s 2>/dev/null && cat %s'" % (TMP, TMP), 35)
    r = sh("cat %s 2>/dev/null" % TMP, 10)
    xml = r.stdout or ""
    if len(xml) < 100:
        r = sh("shizuku -r sh -c 'cmd accessibility dump 2>/dev/null'", 15)
        xml = r.stdout or xml
    OUT.write_text(xml[:500000])
    also = Path.home() / "broccoli/ui/latest.xml"
    also.parent.mkdir(parents=True, exist_ok=True)
    also.write_text(xml[:500000])
    print("DUMP", len(xml), str(OUT))
    return xml

def find_text(xml, needle):
    hits = []
    for m in re.finditer(r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        if needle.lower() in m.group(1).lower():
            x1,y1,x2,y2 = map(int, m.groups()[1:])
            hits.append((m.group(1), (x1+x2)//2, (y1+y2)//2))
    return hits

def tap(x, y):
    sh("shizuku -r sh -c 'input tap %d %d'" % (x, y), 10)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dump"
    if cmd == "dump":
        dump()
    elif cmd == "tap-text" and len(sys.argv) > 2:
        xml = OUT.read_text() if OUT.is_file() else dump()
        h = find_text(xml, sys.argv[2])
        if not h:
            sys.exit(1)
        tap(h[0][1], h[0][2])
        print("TAP", h[0])
    else:
        print("usage: dump | tap-text Send")
