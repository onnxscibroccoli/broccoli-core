#!/usr/bin/env python3
"""Front path: 1–2 dumps max, then cache PASS. Skip grok-smoke poll loop."""
import json, subprocess, sys, time
from pathlib import Path
HOME = Path.home()
ROOT = HOME / "broccoli"
sys.path.insert(0, str(ROOT / "lib"))
from grok_xml_parse import find_smoke_ok, extract_hierarchy
try:
    from toast import step, toast
except Exception:
    def step(m): print(m, flush=True)
    def toast(m): print(m, flush=True)

def main():
    step("Smoke fast")
    meta = ROOT / "meta" / "smoke_cache.json"
    if meta.exists():
        try:
            c = json.loads(meta.read_text())
            if c.get("status") == "PASS" and (time.time() - c.get("healed_at", 0)) < 86400:
                toast("Smoke cached PASS")
                print("PASS cached")
                return 0
        except Exception:
            pass
    boot = HOME / "broccoli_bootstrap.py"
    ui = ROOT / "ui"
    for _ in range(2):
        r = subprocess.run([sys.executable, str(boot), "dump_ui"], timeout=60, capture_output=True, text=True)
        raw = (r.stdout or "") + (r.stderr or "")
        xml = extract_hierarchy(raw)
        if not xml:
            continue
        (ui / "last_ui.xml").write_text(xml, errors="replace")
        hit = find_smoke_ok(xml)
        if hit:
            c = {"status": "PASS", "reply": hit, "healed_at": time.time(), "reason": "smoke_fast"}
            meta.parent.mkdir(parents=True, exist_ok=True)
            meta.write_text(json.dumps(c, indent=2))
            (ROOT / "reports" / "smoke_last.txt").write_text(f"PASS {hit} (smoke_fast)\n")
            toast("Smoke PASS")
            print("PASS", hit)
            return 0
        subprocess.run([sys.executable, str(boot), "scroll_chat_end"], timeout=25, capture_output=True)
    from smoke_autoheal import heal_smoke
    c = heal_smoke()
    toast("Smoke " + c.get("status", "?"))
    return 0 if c.get("status") == "PASS" else 1

if __name__ == "__main__":
    sys.exit(main())
