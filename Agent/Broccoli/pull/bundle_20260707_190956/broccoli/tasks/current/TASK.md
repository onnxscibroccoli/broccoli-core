# Task: google-ai-reliable
id: google-ai-reliable
provider: google
phase: research
max_rounds: 20
acceptance:
  - test -f ~/broccoli/research/notes.md
  - test $(wc -l < ~/broccoli/research/notes.md) -ge 8
  - brocc google-smoke PASS or notes from last google OK report

## Goal
Use Google app Search -> AI Mode (NOT Gemini app) for answers.
Append each OK reply to ~/broccoli/research/notes.md.
Grok only for Broccoli patches when inbox/grok has patch jobs.

## User must
WAIT_FOR_USER: Sign in to Google / open AI Mode if job stalls on login wall.
