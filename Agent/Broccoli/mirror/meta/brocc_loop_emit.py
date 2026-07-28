
#!/usr/bin/env python3
import json, subprocess, sys, time, importlib.util
from pathlib import Path
H, META = Path.home(), Path.home() / "broccoli/meta"
FORCE = "--force" in sys.argv

def fp():
    m = Path.home() / "broccoli"
    return str(sum((p.stat().st_size + int(p.stat().st_mtime)) for p in m.rglob("*") if p.is_file()) % 10**12) if m.is_dir() else "0"

spec = importlib.util.spec_from_file_location("bs", H / "broccoli_storage_sync.py")
bs = importlib.util.module_from_spec(spec); sys.modules["bs"] = bs; spec.loader.exec_module(bs)
spec2 = importlib.util.spec_from_file_location("st", META / "brocc_state.py")
st = importlib.util.module_from_spec(spec2); sys.modules["st"] = spec2; spec2.loader.exec_module(st)

report, _ = bs.verify()
state = st.load()
fingerprint = fp()
report["phase"] = state["phase"]
if not FORCE and not st.should_emit(report, fingerprint):
    print("EMIT_SKIP"); sys.exit(0)

packet = {
    "role": "brocc", "ts": time.strftime("%F %T"), "phase": state["phase"],
    "summary": {"missing": report.get("missing"), "stale": report.get("stale"), "ok": report.get("ok")},
    "ask_grok": "Reply with grok_commands.sh lines only (brocc/python3). Mac: adb push to inbox/from_mac/grok_commands.sh",
    "mac_pull": report.get("mac_pull", []),
}
pack = META / "loop_packet.json"
to_mac = META / "inbox/to_mac/loop_packet.json"
pack.write_text(json.dumps(packet, indent=2))
to_mac.write_text(pack.read_text())
(Path("/sdcard/Broccoli/pull/loop_packet.json")).write_text(pack.read_text())
st.mark_emit(report, fingerprint)
body = pack.read_text()[:12000]
(Path("/sdcard/Broccoli/pull/CLIPBOARD_LAST.txt")).write_text(body)
try:
    spec3 = importlib.util.spec_from_file_location("bc", H / "broccoli_clipboard.py")
    bc = importlib.util.module_from_spec(spec3); sys.modules["bc"] = spec3; spec3.loader.exec_module(bc)
    bc.set(body, toast=False)
except Exception:
    pass


# CLIP_PROMPT_INTERJECT — newest prompt to clipboard for manual start
import os as _cp_os
if _cp_os.environ.get("BROCC_CLIP_PROMPT", "1") != "0":
    try:
        import subprocess as _cp_sp, sys as _cp_sys
        from pathlib import Path as _cp_P
        _cp_sp.run([_cp_sys.executable, str(_cp_P.home() / "broccoli_clip_prompt.py")], timeout=45, check=False)
    except Exception as _cp_e:
        print("CLIP_PROMPT_ERR", _cp_e)

# PHONE_GROK_AUTO_PASTE — after every EMIT_OK (disable: export BROCC_PHONE_GROK=0)
import os as _os_emit
if (_os_emit.environ.get("BROCC_PHONE_GROK", "0") == "1" and _os_emit.environ.get("BROCC_CLIP_PROMPT", "1") == "0"):
    try:
        import subprocess as _sp, sys as _sys
        _sp.run([_sys.executable, str(Path.home() / "broccoli_phone_grok_send.py")],
                input=body, text=True, timeout=180, check=False)
    except Exception as _e:
        print("PHONE_GROK_PASTE_ERR", _e)

print("EMIT_OK", pack)
