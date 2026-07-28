#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
META="$HOME/broccoli/meta"
FORCE="${1:-}"
PY=python3
PACK="$META/loop_packet.json"
TO_MAC="$META/inbox/to_mac"

mkdir -p "$TO_MAC"
REPORT="$($PY "$META/broccoli_storage_sync.py" verify 2>/dev/null | tail -1)" || true
$PY "$META/broccoli_storage_sync.py" verify >/dev/null

$PY - <<'PY'
import json, time, importlib.util
from pathlib import Path

def load_state():
    spec = importlib.util.spec_from_file_location("brocc_state", Path.home()/"broccoli/meta/brocc_state.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

man = Path("/sdcard/Broccoli/mirror_manifest.json")
report = json.loads(man.read_text()) if man.is_file() else {}
st = load_state()
state = st.load()
force = "__FORCE__" in open("/proc/self/environ", "rb").read().decode("latin-1", "ignore") or False

# fingerprint: cheap tree tick
meta = Path.home() / "broccoli"
fp = str(sum(p.stat().st_mtime for p in meta.rglob("*") if p.is_file()) % 10**9) if meta.is_dir() else "0"

summary = {
    "src_gb": report.get("src_gb"),
    "missing": report.get("missing"),
    "stale": report.get("stale"),
    "ok": report.get("ok"),
    "phase": state["phase"],
}
report["summary"] = summary

import os
force = os.environ.get("BROCC_EMIT_FORCE") == "1"
if not force and not st.should_emit(report, fp):
    print("EMIT_SKIP unchanged or phase not await_grok")
    raise SystemExit(0)

packet = {
    "role": "brocc",
    "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    "phase": state["phase"],
    "summary": summary,
    "ask_grok": "Reply with file grok_commands.sh lines
