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
import json, time
from pathlib import Path
root = Path.home() / "broccoli-core"
meta = root / "meta" / "always_on"
meta.mkdir(parents=True, exist_ok=True)
payload = {
    "timestamp": int(time.time()),
    "assist_mode": "ready",
    "note": "always_on supervisor pulse; assist when AI transports healthy",
}
try:
    from runtime.governor.runtime_health_governor import RuntimeHealthGovernor
    s = RuntimeHealthGovernor().collect()
    payload["health_overall"] = s.overall_status
    payload["required"] = [
        {"name": c.name, "status": c.status, "age": round(getattr(c, "age_seconds", 0) or 0, 1)}
        for c in s.components if c.required
    ]
    payload["assist_mode"] = "active" if s.overall_status in ("RUNTIME_OK", "HEALTH_WARNING") else "degraded"
except Exception as e:
    payload["assist_mode"] = "degraded"
    payload["error"] = str(e)
(meta / "assist.json").write_text(json.dumps(payload, indent=2))
print("assist_mode=" + payload["assist_mode"])
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
