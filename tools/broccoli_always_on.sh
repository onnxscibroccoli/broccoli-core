#!/data/data/com.termux/files/usr/bin/bash
# Broccoli Core always-on supervisor.
# Keeps runtime.main alive, heartbeats drive_sync, rotates processed events,
# and records an assist pulse when AI transports look healthy.
set -euo pipefail
ROOT="${HOME}/broccoli-core"
META="${ROOT}/meta/always_on"
LOG="${META}/supervisor.log"
PIDFILE="${META}/runtime.pid"
ASSIST="${META}/assist.json"
cd "$ROOT" || exit 1
mkdir -p "$META"
export PYTHONPATH="$ROOT"

log() { echo "$(date -Is) $*" | tee -a "$LOG"; }

free_mb() {
  # Termux: prefer 1K-blocks from df -k, convert to MiB
  df -k "$ROOT" 2>/dev/null | awk 'NR==2{printf "%d", $4/1024}'
}

runtime_alive() {
  if [ -f "$PIDFILE" ]; then
    pid=$(cat "$PIDFILE" 2>/dev/null || true)
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

start_runtime() {
  free=$(free_mb || echo 0)
  if [ "${free:-0}" -lt 400 ]; then
    log "SKIP start: free_mb=${free} (<400)"
    return 1
  fi
  log "START runtime.main"
  nohup python3 -u -m runtime.main >>"$META/runtime.log" 2>&1 &
  echo $! >"$PIDFILE"
  log "PID $(cat "$PIDFILE")"
}

assist_pulse() {
  PYTHONPATH="$ROOT" python3 - <<'END' || true
import json, re, subprocess, time
from pathlib import Path

AI_PACKAGES = (
    "ai.x.grok",
    "com.openai.chatgpt",
    "com.anthropic.claude",
    "com.google.android.apps.bard",
    "com.microsoft.copilot",
)

root = Path.home() / "broccoli-core"
meta = root / "meta" / "always_on"
meta.mkdir(parents=True, exist_ok=True)

def detect_foreground():
    """Best-effort foreground package. Prefer rish; fall back to dumpsys."""
    cmds = [
        ["rish", "-c", "dumpsys activity activities"],
        ["rish", "-c", "dumpsys window windows"],
        ["dumpsys", "activity", "activities"],
    ]
    text = ""
    for cmd in cmds:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            if r.returncode == 0 and (r.stdout or "").strip():
                text = r.stdout
                break
        except Exception:
            continue
    if not text:
        return None, "unavailable"
    # mResumedActivity / topResumedActivity / mFocusedApp
    patterns = [
        r"topResumedActivity.*?\s+([a-zA-Z0-9_.]+)/",
        r"mResumedActivity.*?\s+([a-zA-Z0-9_.]+)/",
        r"mFocusedApp.*?\s+([a-zA-Z0-9_.]+)/",
        r"ResumedActivity:\s*ActivityRecord\{[^ ]+\s+[^ ]+\s+([a-zA-Z0-9_.]+)/",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1), "detected"
    return None, "unknown"

fg_pkg, fg_src = detect_foreground()
ai_in_use = bool(fg_pkg and any(fg_pkg == p or fg_pkg.startswith(p + ".") for p in AI_PACKAGES))

payload = {
    "timestamp": int(time.time()),
    "assist_mode": "ready",
    "note": "always_on assist pulse",
    "foreground_package": fg_pkg,
    "foreground_source": fg_src,
    "ai_tool_in_use": ai_in_use,
}
try:
    from runtime.governor.runtime_health_governor import RuntimeHealthGovernor
    s = RuntimeHealthGovernor().collect()
    payload["health_overall"] = s.overall_status
    payload["required"] = [
        {"name": c.name, "status": c.status, "age": round(getattr(c, "age_seconds", 0) or 0, 1)}
        for c in s.components if c.required
    ]
    healthy = s.overall_status in ("RUNTIME_OK", "HEALTH_WARNING")
    if not healthy:
        payload["assist_mode"] = "degraded"
    elif ai_in_use:
        payload["assist_mode"] = "assisting"
        payload["note"] = f"AI tool in foreground: {fg_pkg}"
    else:
        payload["assist_mode"] = "active"
        payload["note"] = "runtime healthy; assist ready for AI tools"
except Exception as e:
    payload["assist_mode"] = "degraded"
    payload["error"] = str(e)

(meta / "assist.json").write_text(json.dumps(payload, indent=2))
print(
    "assist_mode={mode} ai_in_use={ai} fg={fg}".format(
        mode=payload["assist_mode"], ai=ai_in_use, fg=fg_pkg
    )
)
END
}

# housekeeping every cycle
bash tools/drive_sync_heartbeat.sh >/dev/null 2>&1 || true
bash tools/rotate_processed_events.sh 50 >/dev/null 2>&1 || true
bash tools/repository_health.sh >/dev/null 2>&1 || true

if runtime_alive; then
  log "ALIVE pid=$(cat "$PIDFILE")"
else
  log "DEAD or missing — restarting"
  start_runtime || true
fi

assist_pulse
log "cycle done free_mb=$(free_mb || echo ?)"
