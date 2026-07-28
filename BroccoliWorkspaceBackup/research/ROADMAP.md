# Broccoli stabilization roadmap

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 (smoke PASS)
  │            │            │            │
  healer      pulse/       Shizuku VD   sanitizer
  paths       clip/report  coord map    git init
```

| Phase | Deliverable | Verify |
|-------|-------------|--------|
| 1 | `scripts/broccoli_storage_healer.sh`, `path_validate.sh` | internal partition only |
| 2 | `broccoli_pulse.py`, `clip_promt.py`, `broccoli_report.py` | no timeout; brackets OK |
| 3 | `shizuku_vd_config.json`, coordinate map | injection smoke |
| 4 | `offline_sanitizer.py`, `.gitignore` | no secrets in git |
| 5 | `notes.md` ≥5 lines, `grok-smoke` | **PASS** |

Dependency: KXT (`modules/kxt_xxd.py`) consumes **xxd** output for security blob checks.
