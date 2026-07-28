# UI dump loop (Broccoli / Grok / Mac)

## Purpose
Continuous **synchronous** UI context for wire decisions and Mac co-dev.
Not a substitute for `brocc send` — dump informs **when** and **what** is on screen.

## Artifacts (phone)
| File | Role |
|------|------|
| `reports/ui_dump.xml` | Raw uiautomator / brocc dump |
| `reports/wire_context.json` | Parsed composer + Send bounds |
| `reports/ui_snapshot.json` | TS, queue_bytes, foreground, context |
| `reports/ui_dump_loop.log` | Loop decisions (SKIP/OK) |

## Optimization
- Dump faster when `queue/agent_task.txt` non-empty (`DUMP_INTERVAL_SEC`).
- Skip parse when XML hash unchanged (`SKIP_IF_XML_UNCHANGED`).
- Skip when Grok not foreground (`DUMP_ONLY_IF_FOREGROUND`).

## Mac agent
1. Pull `ui_snapshot.json` + `ui_dump.xml` (rsync/git).
2. `consume_response` on Grok thread exports.
3. Append research to `docs/RESEARCH_LOG.md` and `reports/research/*.md`.
4. Push next task to `queue/agent_task.txt`.

## Grok (mobile)
Receives tasks via **broccoli_agent** → `brocc send` after foreground.
Reply token: `BROCCOLI_LOOP_OK`.

## rish / Shizuku
`uiautomator dump` + `cat` via `rish -c`; optional `brocc dump` first.
