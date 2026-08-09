# DO Spike — Broccoli off-device workspace

Goal: one Durable Object with a durable SQLite VFS via @cloudflare/computer.
No container backend yet. Prove: create files, survive restart, expose HTTP read/write.

## Scope

- Worker + Durable Object
- Workspace with fs only (no runtime backends)
- Endpoints: POST /write, GET /read, GET /ls
- Result contract v0: JSON body { path, content } → durable file under /workspace

## Next after green

1. Add isolate-shell backend (just-bash Dynamic Worker)
2. Define artifact export → GitHub (receipt push)
3. Multi-LLM planner that writes plans into the workspace
