# broccoli-core
Broccoli Core - Android Automation Framework

---

## Production (live Grok from Termux)

Tokens: `~/.broccoli/xai_oauth_tokens.json` (mode 600, never commit).

```bash
cd "$HOME/broccoli-core"
git pull origin main
chmod +x bin/broccoli bin/xai-oauth bin/brocc

./bin/broccoli status
./bin/broccoli ping
./bin/broccoli ask "Say hello from Broccoli Core."
```

`broccoli` talks to the real xAI API through GrokProvider + EventBus.
It does not boot accessibility or the Governor.

See `docs/PRODUCTION.md`.

## xAI / Grok OAuth (Termux)

Do **not** use `cd \~/broccoli-core` — the backslash makes `~` literal and the cd fails.

```bash
cd "$HOME/broccoli-core"
./bin/xai-oauth login
./bin/xai-oauth status
```

GrokProvider uses that OAuth session first and only falls back to `XAI_API_KEY` (a separate metered ledger).

---

# Organic Problem Solver

Broccoli Core now supports a provider-agnostic problem solving pipeline.

Future collectors should publish evidence rather than directly solving problems.

## Managed transports

Runtime components that expose `start()`, `stop()`, and `health()` are managed as transports. The managed set includes the accessibility driver, clipboard bridge, Grok provider, workflow executor, adaptive planner, knowledge graph, agent coordinator, and plugin loader.
