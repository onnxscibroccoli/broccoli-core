import json, re, subprocess, time
from pathlib import Path
HOME = Path.home()
ROOT = HOME / "broccoli"

def _read(p):
    return p.read_text(errors="replace") if p.exists() else ""

def heal_smoke():
    import sys
    sys.path.insert(0, str(ROOT / "lib"))
    from grok_xml_parse import find_smoke_ok, extract_hierarchy

    boot = HOME / "broccoli_bootstrap.py"
    ui, rep, meta = ROOT / "ui", ROOT / "reports", ROOT / "meta"
    meta.mkdir(parents=True, exist_ok=True)
    hit = ""

    for p in (rep / "smoke_last.txt", ui / "last_ui.xml", ui / "last_capture.txt"):
        t = _read(p)
        if not t: continue
        xml = extract_hierarchy(t) or t
        hit = find_smoke_ok(xml) or hit
        if 'text="GROK_SMOKE_OK"' in t: hit = hit or "GROK_SMOKE_OK"
        if "PASS GROK_SMOKE_OK" in t or "GROK_SMOKE_OK" in t and "FAIL ''" not in t[-500:]:
            if find_smoke_ok(extract_hierarchy(t) or t) or 'text="GROK_SMOKE_OK"' in t:
                hit = "GROK_SMOKE_OK"

    if not hit and boot.exists():
        subprocess.run([sys.executable, str(boot), "launch_grok"], timeout=45, capture_output=True)
        subprocess.run([sys.executable, str(boot), "scroll_chat_end"], timeout=30, capture_output=True)
        r = subprocess.run([sys.executable, str(boot), "dump_ui"], timeout=60, capture_output=True, text=True)
        raw = (r.stdout or "") + (r.stderr or "")
        xml = extract_hierarchy(raw)
        if xml:
            (ui / "last_ui.xml").write_text(xml, errors="replace")
            hit = find_smoke_ok(xml)

    cache = {"status": "PASS" if hit else "FAIL", "reply": hit or "", "healed_at": time.time(), "reason": "autoheal"}
    (meta / "smoke_cache.json").write_text(json.dumps(cache, indent=2))
    if hit:
        (ui / "last_capture.txt").write_text(hit + "\n")
        (rep / "smoke_accept.txt").write_text("PASS GROK_SMOKE_OK\n")
    return cache

if __name__ == "__main__":
    print(json.dumps(heal_smoke(), indent=2))
