
#!/usr/bin/env python3
import json, time
from pathlib import Path
R = Path.home() / "broccoli"
INBOX = R / "mac" / "inbox.jsonl"
PROCESSED = R / "mac" / "processed.jsonl"

def drain():
    if not INBOX.is_file():
        return 0
    lines = [ln for ln in INBOX.read_text(errors="replace").splitlines() if ln.strip()]
    if not lines:
        return 0
    n = 0
    for ln in lines:
        try:
            job = json.loads(ln)
        except Exception:
            continue
        body = job.get("body", "")
        if job.get("attach_context"):
            import subprocess
            p = subprocess.run(["python3", str(Path.home() / "broccoli_agent_context.py"), "collect"],
                               capture_output=True, text=True, timeout=120)
            body = "AGENT_CONTEXT: %s\n\n%s" % ((p.stdout or "").strip(), body)
        typ = job.get("type", "grok")
        dest = R / "inbox" / ("grok" if typ == "grok" else "google")
        dest.mkdir(parents=True, exist_ok=True)
        f = dest / ("%d_mac.json.txt" % time.time())
        f.write_text(body[:50000])
        n += 1
    PROCESSED.write_text("\n".join(lines) + "\n", encoding="utf-8")
    INBOX.write_text("")
    return n

if __name__ == "__main__":
    print("ingested", drain())
