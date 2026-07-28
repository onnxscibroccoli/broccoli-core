# Broccoli HANDOFF
Task: deep-research-pilot (google research)
Acceptance: research/notes.md ≥5 lines; grok-smoke PASS
Stack: brocc, daemon, worker, bootstrap, grok_job, compose SLIM, google_ai_bootstrap, research, user_wait, meta, resilience, accept
Rules: scroll before read; empty/junk FAIL; send=tap; smoke GROK_SMOKE_OK; SLIM for grok jobs; TERMINUX no markdown fences
Cmds: brocc focus|recover|smoke|run-once|report|research round|user-wait|user-done|doctor
Artifacts: research/notes.md, reports/latest.txt, WAITING_USER.txt
Mac: HANDOFF + report each new chat; co-dev patches + toasts on phone
