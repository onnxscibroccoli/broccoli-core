
#!/usr/bin/env python3
"""Optimized UI dump loop: foreground gate, hash skip, snapshot for Mac/Grok agent."""
import hashlib, json, re, subprocess, sys, time, shutil
from pathlib import Path
from xml.etree import ElementTree as ET

B = Path.home() / "broccoli"
ENV = B / "meta/dump_loop.env"
XML = B / "reports/ui_dump.xml"
CTX = B / "reports/wire_context.json"
SNAP = B / "reports/ui_snapshot.json"
LOG = B / "reports/ui_dump_loop.log"
Q = B / "queue/agent_task.txt"
LAST_HASH = B / "reports/.ui_dump_hash"

def log(m):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {m}\n")

def cfg():
    o = {"GROK_PKG": "ai.x.grok", "DUMP_INTERVAL_SEC": "3", "DUMP_INTERVAL_IDLE_SEC": "10",
         "DUMP_ONLY_IF_FOREGROUND": "1", "SKIP_IF_XML_UNCHANGED": "1"}
    if ENV.is_file():
        for line in ENV.read_text(errors="replace").splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                o[k.strip()] = v.strip()
    return o

def rish(c, t=45):
    return subprocess.run(["rish", "-c", c], capture_output=True, text=True, timeout=t)

def sync_dump():
    if shutil.which("brocc"):
        subprocess.run(["brocc", "dump"], capture_output=True, text=True, timeout=90)
    if not XML.is_file() or XML.stat().st_size < 500:
        rish("uiautomator dump /data/local/tmp/broccoli_ui.xml")
        r = rish("cat /data/local/tmp/broccoli_ui.xml")
        if r.stdout and len(r.stdout) > 500:
            XML.write_text(r.stdout, encoding="utf-8", errors="replace")
    return XML.is_file() and XML.stat().st_size > 500

def parse_context(raw: str) -> dict:
    composer = send = None
    pkg = ""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return {"package": "", "composer": None, "send": None}
    def nums(s):
        m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", s or "")
        return tuple(map(int, m.groups())) if m else None
    def area(b):
        return (b[2]-b[0])*(b[3]-b[1]) if b else 0
    sends = []
    for n in root.iter():
        pkg = n.attrib.get("package") or pkg
        cls = n.attrib.get("class") or ""
        b = nums(n.attrib.get("bounds"))
        if not b:
            continue
        if "EditText" in cls:
            if composer is None or area(b) > area(composer["bounds"]):
                composer = {"text": (n.attrib.get("text") or "")[:500], "bounds": list(b)}
        lab = (n.attrib.get("content-desc") or n.attrib.get("text") or "").strip()
        if re.search(r"(?i)send|submit", lab):
            sends.append({"label": lab, "bounds": list(b)})
    if sends:
        send = sends[-1]
    return {"package": pkg, "composer": composer, "send": send}

def grok_foreground(raw: str, pkg: str) -> bool:
    return pkg in raw or "grok" in raw.lower() or "ai.x.grok" in raw

def snapshot(ctx: dict, queue_bytes: int, changed: bool):
    snap = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "queue_bytes": queue_bytes,
        "dump_changed": changed,
        "foreground_grok": grok_foreground(XML.read_text(errors="replace"), ctx.get("package", "")),
        "wire_context": ctx,
    }
    SNAP.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    CTX.write_text(json.dumps(ctx, indent=0), encoding="utf-8")

def content_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]

def tick(force=False):
    c = cfg()
    pkg = c.get("GROK_PKG", "ai.x.grok")
    qbytes = Q.stat().st_size if Q.is_file() else 0
    if not sync_dump():
        log("SKIP dump_fail")
        return
    raw = XML.read_text(errors="replace")
    if c.get("DUMP_ONLY_IF_FOREGROUND", "1") == "1" and not grok_foreground(raw, pkg):
        log("SKIP not_foreground")
        return
    h = content_hash(raw)
    prev = LAST_HASH.read_text().strip() if LAST_HASH.is_file() else ""
    changed = h != prev
    if c.get("SKIP_IF_XML_UNCHANGED", "1") == "1" and not changed and not force:
        log("SKIP unchanged")
        return
    LAST_HASH.write_text(h)
    ctx = parse_context(raw)
    snapshot(ctx, qbytes, changed)
    log(f"OK dump composer={bool(ctx.get('composer'))} send={bool(ctx.get('send'))} q={qbytes} changed={changed}")

def loop():
    log("OK ui_dump_loop started")
    last_q = -1
    while True:
        c = cfg()
        qbytes = Q.stat().st_size if Q.is_file() else 0
        if c.get("DUMP_ON_QUEUE_CHANGE", "1") == "1" and qbytes != last_q and qbytes > 0:
            tick(force=True)
            last_q = qbytes
        else:
            tick(force=False)
            last_q = qbytes
        interval = float(c.get("DUMP_INTERVAL_SEC", "3") if qbytes > 0 else c.get("DUMP_INTERVAL_IDLE_SEC", "10"))
        time.sleep(interval)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        tick(force=True)
        sys.exit(0)
    loop()
