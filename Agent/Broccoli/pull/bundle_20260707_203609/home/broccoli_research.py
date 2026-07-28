
#!/usr/bin/env python3
"""Deep research orchestration: queue google/grok, merge OK reports into notes."""
import json, re, subprocess, sys, time
from pathlib import Path

H, R = Path.home(), Path.home() / "broccoli"
NOTES = R / "research" / "notes.md"
SOURCES = R / "research" / "sources.txt"
TASK = R / "tasks" / "current" / "TASK.md"

def run(cmd, t=180):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)

def task_meta():
    if not TASK.is_file():
        return {}
    t = TASK.read_text(errors="replace")
    m = {}
    for line in t.splitlines():
        if line.startswith("id:"):
            m["id"] = line.split(":", 1)[1].strip()
        if line.startswith("provider:"):
            m["provider"] = line.split(":", 1)[1].strip()
        if "phase:" in line:
            m["phase"] = line.split(":", 1)[1].strip()
    return m

def append_note(provider, job, reply):
    reply = (reply or "").strip()
    if not reply or reply in ("(empty reply)", "junk reply"):
        return
    if "=== BROCCOLI REPORT ===" in reply:
        reply = reply.split("=== BROCCOLI REPORT ===")[0].strip()
    ts = time.strftime("%Y-%m-%d %H:%M")
    block = "\n\n## %s | %s | %s\n%s\n" % (ts, provider, job, reply[:8000])
    with open(NOTES, "a", encoding="utf-8") as f:
        f.write(block)
    urls = re.findall(r"https?://[^\s\]>\"]+", reply)
    if urls:
        with open(SOURCES, "a", encoding="utf-8") as f:
            for u in urls[:30]:
                f.write(u + "\n")

def enqueue_google(query):
    R.mkdir(parents=True, exist_ok=True)
    f = R / "inbox" / "google" / ("%d_research.txt" % time.time())
    f.write_text(query.strip()[:4000])
    return str(f)

def enqueue_grok(prompt):
    f = R / "inbox" / "grok" / ("%d_research.txt" % time.time())
    f.write_text(prompt.strip()[:4000])
    return str(f)

def google_job(query):
    """Use existing google_ai_bootstrap if present."""
    g = H / "google_ai_bootstrap.py"
    if not g.is_file():
        return 1, "missing google_ai_bootstrap.py"
    r = run('python3 "%s" ask "%s"' % (g, query.replace('"', '\\"')[:3500]))
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    return (0 if r.returncode == 0 and len(out) > 20 else 1), out[:12000]

def grok_job(prompt):
    j = H / "broccoli_grok_job.py"
    if j.is_file():
        r = run('python3 "%s" "%s"' % (j, prompt.replace('"', '\\"')[:3500]))
        out = (r.stdout or "").strip()
        return (0 if r.returncode == 0 and out else 1), out
    r = run('python3 "%s" grok-ask "%s"' % (H / "broccoli_bootstrap.py", prompt.replace('"', '\\"')[:3500]))
    out = (r.stdout or "").strip()
    return (0 if r.returncode == 0 and out else 1), out

def round_research(topic=None):
    meta = task_meta()
    topic = topic or meta.get("id", "research")
    if not TASK.is_file():
        return "no TASK.md"
    body = TASK.read_text(errors="replace")
    # extract ## Goal or first paragraph after Goal
    goal = topic
    if "## Goal" in body:
        goal = body.split("## Goal", 1)[1].split("##", 1)[0].strip()[:2000]

    prov = meta.get("provider", "google").lower()
    if prov == "google" or "google" in body.lower():
        q = "Research concisely with sources cited:\n" + goal
        path = enqueue_google(q)
        return "queued google %s" % path
    path = enqueue_grok(
        "LOOP_OK\nNEXT_STEP: merge research\n"
        "Summarize progress for notes.md in 8 bullets. Topic:\n" + goal[:1500]
    )
    return "queued grok %s" % path

def doctor():
    issues = []
    for name in ("broccoli_bootstrap.py", "broccoli_worker.sh", "brocc"):
        if not (H / name).is_file():
            issues.append("missing:" + name)
    if not (H / "google_ai_bootstrap.py").is_file():
        issues.append("warn:no_google_ai_bootstrap")
    r = run("python3 ~/broccoli_bootstrap.py grok-smoke 2>&1 | tail -5")
    smoke = "PASS" in (r.stdout or "") + (r.stderr or "")
    print("smoke", "PASS" if smoke else "FAIL")
    print("issues", issues or "none")
    print("notes", NOTES, "lines", len(NOTES.read_text().splitlines()) if NOTES.is_file() else 0)
    return 0 if smoke else 1

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "doctor":
        sys.exit(doctor())
    if cmd == "round":
        print(round_research(sys.argv[2] if len(sys.argv) > 2 else None))
        return
    if cmd == "enqueue-google":
        print(enqueue_google(" ".join(sys.argv[2:])))
        return
    if cmd == "enqueue-grok":
        print(enqueue_grok(" ".join(sys.argv[2:])))
        return
    if cmd == "merge-last":
        rep = R / "reports" / "latest.txt"
        if rep.is_file():
            t = rep.read_text(errors="replace")
            reply = ""
            for line in t.splitlines():
                if line.startswith("reply: "):
                    reply = line[7:]
                    break
            prov = "grok"
            if "provider: google" in t:
                prov = "google"
            append_note(prov, "latest", reply)
            print("merged", len(reply))
        return
    print("usage: doctor|round|enqueue-google|enqueue-grok|merge-last")

if __name__ == "__main__":
    main()
