
#!/usr/bin/env python3
import json, subprocess, time
from pathlib import Path
R = Path.home() / "broccoli"
AG = R / "agent"

def sh(cmd, t=25):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)

def collect():
    AG.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    ctx = {"ts": ts, "focus": "", "ui_len": 0, "log_tail": ""}
    o = sh("shizuku -r sh -c 'dumpsys window 2>/dev/null | grep -E mCurrentFocus|mFocusedApp'")
    ctx["focus"] = (o.stdout or o.stderr or "")[:2000]
    o = sh("shizuku -r sh -c 'dumpsys activity top 2>/dev/null | head -40'")
    ctx["activity_top"] = (o.stdout or "")[:3000]
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("bb", Path.home() / "broccoli_bootstrap.py")
        bb = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bb)
        if hasattr(bb, "scroll_chat_end"):
            bb.scroll_chat_end(1)
        xml = bb.dump_ui() if hasattr(bb, "dump_ui") else ""
        (R / "ui" / "latest.xml").write_text((xml or "")[:400000])
        ctx["ui_len"] = len(xml or "")
    except Exception as e:
        ctx["ui_error"] = str(e)
    log = R / "daemon.log"
    if log.is_file():
        ctx["log_tail"] = "\n".join(log.read_text(errors="replace").splitlines()[-40:])
    cal = Path.home() / ".grok_ui_cal.json"
    if cal.is_file():
        ctx["cal"] = json.loads(cal.read_text())
    out = AG / ("context_%s.json" % ts)
    out.write_text(json.dumps(ctx, indent=2))
    print(str(out))
    return str(out)

if __name__ == "__main__":
    import sys
    if sys.argv[-1] == "collect":
        collect()
