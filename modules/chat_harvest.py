#!/usr/bin/env python3
"""
Phase 1 orchestrator: pull responses from current chat (all-chats = future nav module).
Never runs send/tap. Always exits 0 with report unless BROCC_STRICT=1.
"""
import os, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

def ensure_grok():
    import subprocess, time
    from modules.state_probe import probe
    for i in range(12):
        st = probe(refresh=(i % 3 == 0))
        if st.get("in_grok_chat") and not st.get("new_chat_focused"):
            return st
        if i % 4 == 0:
            subprocess.run(["bash", "grok_launch.sh"], cwd=ROOT, timeout=28, capture_output=True)
        else:
            subprocess.run(["bash", "lib/rish_cmd.sh", "am start -n ai.x.grok/.MainActivity"],
                             cwd=ROOT, timeout=10, capture_output=True)
        time.sleep(0.8)
    return probe(refresh=True)

def main():
    import os
    from modules.registry import Ctx, ModuleResult
    from modules import state_probe, chat_nav, ui_dump, chat_reader, chat_store

    os.environ.setdefault("BROCC_VALIDATE_MODE", "grace")
    st = ensure_grok()
    ctx = Ctx(root=ROOT, state=st, env=os.environ.copy())

    log = []
    results = []

    chain = [
        ("state_probe", state_probe.precondition, lambda: ModuleResult(st.get("in_grok_chat"), "state_probe", data=st)),
        ("chat_nav", chat_nav.precondition, chat_nav.run),
        ("ui_dump", ui_dump.precondition, ui_dump.run),
        ("chat_reader", chat_reader.precondition, chat_reader.run),
    ]

    reader_payload = None
    for name, pre, fn in chain:
        ok, reason = pre(st)
        if not ok:
            log.append(f"{name}:SKIP:{reason}")
            results.append({"module": name, "ok": False, "reason": reason})
            if name in ("state_probe", "chat_reader"):
                break
            continue
        if name == "state_probe":
            r = fn()
        else:
            r = fn(ctx)
        results.append({"module": name, "ok": r.ok, "reason": r.reason})
        log.append(f"{name}:{'OK' if r.ok else 'FAIL'}:{r.reason}")
        if name == "chat_reader" and r.data:
            reader_payload = r.data
            ctx.env["_reader_payload"] = r.data

    store_ok = False
    if reader_payload:
        ok, reason = chat_store.precondition(st)
        if ok:
            ctx.env["_reader_payload"] = reader_payload
            sr = chat_store.run(ctx)
            store_ok = sr.ok
            log.append(f"chat_store:{'OK' if sr.ok else 'FAIL'}:{sr.reason}")
            results.append({"module": "chat_store", "ok": sr.ok, "path": (sr.data or {}).get("path")})

    harvest_ok = bool(reader_payload and reader_payload.get("line_count", 0) > 0)
    strict = os.environ.get("BROCC_STRICT") == "1"
    status = "OK" if harvest_ok else ("DEGRADED" if not strict else "FAIL")

    report = f"""=== BROCCOLI HARVEST REPORT ===
time: {datetime.datetime.now().isoformat(timespec="seconds")}
phase: 1_harvest_only
status: {status}
modules: {results}
log: {" | ".join(log)}
line_count: {(reader_payload or {}).get("line_count", 0)}
tail_preview: {((reader_payload or {}).get("tail") or "")[-400:]}
store: {store_ok}
=== END REPORT ===
"""
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    open(os.path.join(ROOT, "reports", "latest_harvest.txt"), "w").write(report)
    open(os.path.join(ROOT, "reports", "latest.txt"), "w").write(report)
    print(report)
    print("===MAC===", harvest_ok or not strict)
    if strict and not harvest_ok:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
