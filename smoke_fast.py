#!/usr/bin/env python3
"""Front path: 1–2 dumps max, then cache PASS. Skip grok-smoke poll loop.

The canonical checkout is this repository (broccoli-core), not a sibling
~/broccoli tree. Cached PASS is honored only for the same parser/script stamp.
"""
import hashlib, json, subprocess, sys, time
from pathlib import Path

def resolve_root() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [here, here.parent, Path.home() / "broccoli-core", Path.home() / "broccoli"]
    for root in candidates:
        if (root / "lib" / "grok_xml_parse.py").is_file():
            return root
    return here

ROOT = resolve_root()
sys.path.insert(0, str(ROOT / "lib"))
from grok_xml_parse import find_smoke_ok, extract_hierarchy
try:
    from toast import step, toast
except Exception:
    def step(m): print(m, flush=True)
    def toast(m): print(m, flush=True)

def contract_stamp() -> str:
    digest = hashlib.sha256()
    for path in (Path(__file__).resolve(), ROOT / "lib" / "grok_xml_parse.py"):
        digest.update(path.read_bytes())
    return digest.hexdigest()

def self_test() -> int:
    if not (ROOT / "lib" / "grok_xml_parse.py").is_file():
        print("SMOKE_FAST_SELF_TEST=FAIL missing grok_xml_parse", ROOT)
        return 1
    sample = '<?xml version="1.0"?><hierarchy text="GROK_SMOKE_OK" bounds="[0,400][10,500]"></hierarchy>'
    if find_smoke_ok(sample) != "GROK_SMOKE_OK":
        print("SMOKE_FAST_SELF_TEST=FAIL parser")
        return 1
    if not extract_hierarchy(sample):
        print("SMOKE_FAST_SELF_TEST=FAIL extract")
        return 1
    print(f"SMOKE_FAST_SELF_TEST=PASS root={ROOT}")
    return 0

def main():
    if "--self-test" in sys.argv:
        return self_test()
    step("Smoke fast")
    meta = ROOT / "meta" / "smoke_cache.json"
    stamp = contract_stamp()
    if meta.exists():
        try:
            c = json.loads(meta.read_text())
            fresh = (time.time() - c.get("healed_at", 0)) < 86400
            if c.get("status") == "PASS" and fresh and c.get("contract") == stamp:
                toast("Smoke cached PASS")
                print("PASS cached")
                return 0
        except Exception:
            pass
    boot = ROOT / "broccoli_bootstrap.py"
    if not boot.is_file():
        boot = Path.home() / "broccoli_bootstrap.py"
    ui = ROOT / "ui"
    for _ in range(2):
        r = subprocess.run([sys.executable, str(boot), "dump_ui"], timeout=60, capture_output=True, text=True)
        raw = (r.stdout or "") + (r.stderr or "")
        xml = extract_hierarchy(raw)
        if not xml:
            continue
        ui.mkdir(parents=True, exist_ok=True)
        (ui / "last_ui.xml").write_text(xml, errors="replace")
        hit = find_smoke_ok(xml)
        if hit:
            c = {"status": "PASS", "reply": hit, "healed_at": time.time(), "reason": "smoke_fast", "contract": stamp}
            meta.parent.mkdir(parents=True, exist_ok=True)
            meta.write_text(json.dumps(c, indent=2))
            reports = ROOT / "reports"
            reports.mkdir(parents=True, exist_ok=True)
            (reports / "smoke_last.txt").write_text(f"PASS {hit} (smoke_fast)\n")
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
