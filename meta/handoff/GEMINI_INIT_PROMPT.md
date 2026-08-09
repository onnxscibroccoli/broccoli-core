# Broccoli Core — Gemini init / on-device protocol

You are continuing onnxscibroccoli/broccoli-core on branch alpha-testing @ 9dc9d64.

## Authority
1. Repo on alpha-testing
2. GitHub issue #12
3. GitHub issue #2
4. meta/gemini, meta/always_on, meta/handoff
5. This prompt (supporting only)

## No connectors
Use gh, git, Termux commands, and device snapshot files only.

## Get device data (user runs)
cd HOME/broccoli-core
bash tools/gemini_device_snapshot.sh
cat meta/gemini/device_snapshot.md

## Grok UI
- package ai.x.grok
- composer chat_text_input
- send: Speak when empty; up-arrow right of mic with text
- dump only valid when packages include ai.x.grok

## Goals G1-G4
1. Grok inject + autonomy rounds
2. AIM_UI_DUMP send path
3. GitHub-tracked milestones on issue #12
4. Smoke truth residual (issue #2)

## Rules
- never git add -A
- launchers via Python chr(36) if chat paste corrupts dollars
- auto-reply opt-in only
- no beta branch until fg=ai.x.grok inject proven
- every batch starts: cd HOME/broccoli-core

## First actions
1. Read issue #12 + SESSION_LESSONS
2. User runs gemini_device_snapshot.sh; paste device_snapshot.md
3. One track: FG/inject validation OR smoke residual
