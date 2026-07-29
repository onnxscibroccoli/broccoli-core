# Patch plan checklist (Phase 2)

## broccoli_pulse.py
- [x] Replace broken loop block at legacy line ~54 with balanced `for i in range(count):` loop
- [x] Log JSON lines to `logs/pulse.log`
- [ ] If you have local diffs: run `python3 -m py_compile broccoli_pulse.py`

## clip_promt.py
- [x] Line ~75: `build_prompt(text, *, max_len=77)` matches core module signature
- [ ] Wire imports if core lives in `modules/core.py` (re-export `build_prompt`)

## broccoli_report.py
- [x] `subprocess.run(..., timeout=30)` for checks
- [x] `subprocess.Popen` for `termux-notification` (non-blocking)
- [ ] Increase timeout only for known-long jobs; never block on notify

## Integration
- [ ] `bash scripts/broccoli_storage_healer.sh`
- [ ] `git init && git add -A` (confirm secrets/ not tracked)
- [ ] `python3 broccoli_bootstrap.py grok-smoke`
