#!/usr/bin/env python3
import re, subprocess, sys
from pathlib import Path

HOME = Path.home()
DUMP_SD = '/data/local/tmp/broccoli_ui.xml'
DUMP_LOCAL = HOME / "broccoli" / "reports" / "last_ui_dump.xml"
BOOT = HOME / "broccoli_bootstrap.py"

def rish_cat_dump():
    script = f"""rm -f /data/local/tmp/broccoli_ui.xml 2>/dev/null
uiautomator dump /data/local/tmp/broccoli_ui.xml 2>/dev/null || cmd uiautomator dump /data/local/tmp/broccoli_ui.xml 2>/dev/null
cat /data/local/tmp/broccoli_ui.xml 2>/dev/null
"""
    p = subprocess.run(["rish"], input=script, capture_output=True, text=True, timeout=90)
    raw = (p.stdout or "") + (p.stderr or "")
    if "<?xml" in raw:
        return raw[raw.find("<?xml"):]
    if "<hierarchy" in raw:
        return raw[raw.find("<hierarchy"):]
    return raw.strip()

def dump_via_bootstrap():
    r = subprocess.run(
        ["python3", str(BOOT), "grok-dump"],
        capture_output=True, text=True, timeout=120,
    )
    t = (r.stdout or "") + (r.stderr or "")
    if "<?xml" in t:
        return t[t.find("<?xml"):]
    return ""

def dump_ui_full():
    DUMP_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    for fn in (dump_via_bootstrap, rish_cat_dump):
        x = fn()
        if x and "<hierarchy" in x:
            DUMP_LOCAL.write_text(x, encoding="utf-8", errors="replace")
            return x
    return ""

def smoke_token(xml):
    if not xml:
        return ""
    if re.search(r'text="GROK_SMOKE_OK"', xml) or re.search(r">GROK_SMOKE_OK<", xml):
        return "GROK_SMOKE_OK"
    return ""

def main():
    op = sys.argv[1] if len(sys.argv) > 1 else ""
    x = dump_ui_full()
    n = len(x)
    print(f"file_bytes {n}", file=sys.stderr)
    if op == "bytes":
        print(n); sys.exit(0 if n > 2000 else 1)
    if op == "smoke-check":
        t = smoke_token(x)
        if t:
            print(t); sys.exit(0)
        print("FAIL no_token", file=sys.stderr)
        sys.exit(1)
    if op == "dump":
        print(x[:500]); sys.exit(0 if n > 2000 else 1)
    sys.exit(2)

if __name__ == "__main__":
    main()
