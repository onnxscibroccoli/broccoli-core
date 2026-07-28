
# HEAL + co-development agent loop

## Grok (device)
- Package: `ai.x.grok`
- Activity: `ai.x.grok.main.GrokActivity` (from resolve-activity or APK)
- Foreground: **`brocc launch-grok`** first (proven). Do NOT use VIEW intent.
- Fallback: `rish -c 'am start -n ai.x.grok/ai.x.grok.main.GrokActivity'`

## Loops
| Process | Role |
|---------|------|
| broccoli_brain.py | Drain queue → foreground → brocc ask/send |
| ui_dump_loop.py | wire_context.json for Mac / rish tap |
| broccoli_supervisor_loop.sh | Respawn brain+dump every 15s |

## Co-dev missions
- Google: inbox/google/* → research/notes.md (Google AI Mode on phone)
- Grok: inbox/grok/* → NEXT_STEP / patches
- Queue: ~/broccoli/queue/agent_task.txt

## Heal one-liner
bash ~/broccoli/tools/broccoli_supervisor.sh && python3 ~/broccoli/tools/broccoli_brain.py once

## Mac pull
reports/wire_context.json, ui_snapshot.json, research/notes.md, docs/HEAL_CODEV_AGENT.md
