
def mac_context_stamp():
    import json, hashlib
    from pathlib import Path
    BRO = Path.home() / "broccoli"
    def sh(p):
        return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.is_file() else ""
    pull = {}
    lp = BRO / "meta/last_pull.json"
    if lp.is_file():
        try:
            pull = json.loads(lp.read_text(encoding="utf-8"))
        except Exception:
            pass
    md = BRO / "MD_CONTEXT.md"
    return "ctx bundle=%s sync=%s walk=%s md=%s" % (
        pull.get("bundle_sha256", sh(BRO / "meta/bundle.sha256"))[:12],
        (pull.get("synced_at") or "")[:19],
        (BRO / "meta/walk_digest.txt").read_text(encoding="utf-8", errors="replace")[:12] if (BRO / "meta/walk_digest.txt").is_file() else "",
        sh(md),
    )

#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
BRO = Path.home() / "broccoli"
sys.path.insert(0, str(BRO / "lib"))
from broccoli_log import append_log
from broccoli_notif import notify, recv_from_grok_notif

LOG = BRO / "reports/infinite.log"
STATE, INBOX = BRO / "state", BRO / "inbox"
POLL = float(os.environ.get("BROCCOLI_POLL_SEC", "45"))

def log(m):
    append_log(LOG, m)

def task():
    p = INBOX / "prompt.txt"
    if p.exists() and p.read_text(encoding="utf-8", errors="replace").strip():
        return p.read_text(encoding="utf-8", errors="replace").strip()
    return "BROCC_TASK reply exactly: LOOP_OK"

def round_once():
    try:
        from broccoli_adb_ui import full_round_adb
        return full_round_adb(task())
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}

def main():
    log("INFINITE_START debugged single_instance poll=%s" % POLL)
    notify("Broccoli", "loop started (Send/Pause/Resume)")
    while not (STATE / "STOP").exists():
        if (STATE / "PAUSE").exists():
            time.sleep(2)
            continue
        if (INBOX / "trigger").exists() or True:
            try:
                INBOX.joinpath("trigger").unlink(missing_ok=True)
            except Exception:
                pass
            t = task()
            log("ROUND task_len=%d" % len(t))
            r = round_once()
            if not r.get("reply") and r.get("ok") is False:
                nr, _ = recv_from_grok_notif(max_wait=12)
                if nr:
                    r["reply"] = nr
                    r["ok"] = "LOOP_OK" in nr or len(nr) > 6
            log("RESULT %s" % json.dumps({k: r.get(k) for k in ("ok", "stage", "loop_ok", "reply_head", "error")})[:400])
            notify("Broccoli", str(r.get("reply_head") or r.get("reply") or r.get("error") or "done")[:80])
        time.sleep(POLL)

if __name__ == "__main__":
    main()
