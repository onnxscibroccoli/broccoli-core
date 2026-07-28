# Task: deep-research-pilot
id: deep-research-pilot
provider: google
phase: research
max_rounds: 20
acceptance:
  - test -f ~/broccoli/research/notes.md
  - test $(wc -l < ~/broccoli/research/notes.md) -ge 5
  - python3 ~/broccoli_bootstrap.py grok-smoke 2>&1 | grep -q PASS

## Goal
Use Google AI Mode on this phone to research: Android UI automation patterns (Shizuku, Termux, accessibility).
Each OK answer: worker merges reply into ~/broccoli/research/notes.md.
Grok jobs only for NEXT_STEP and patching Broccoli.

## Done when
TASK_COMPLETE: research notes.md has sourced bullets; framework still passes smoke.


## User must
(optional) WAIT_FOR_USER: Sign in to Google account in Chrome when job requests it.
