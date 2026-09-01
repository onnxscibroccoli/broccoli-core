# broccoli-core
Broccoli Core - Android Automation Framework

---

## xAI / Grok OAuth (Termux)

Do **not** use `cd \~/broccoli-core` — the backslash makes `~` literal and the cd fails.

```bash
cd "$HOME/broccoli-core"
git pull origin main

# Preferred (sets PYTHONPATH for you):
chmod +x bin/xai-oauth
./bin/xai-oauth login

# Equivalent, from the repo root:
PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}" python -m runtime.providers.xai_oauth login

# Also works from any directory:
python "$HOME/broccoli-core/runtime/providers/xai_oauth.py" login
```

Then open the printed URL, approve the device code, and wait for tokens to save to `~/.broccoli/xai_oauth_tokens.json`.

Check / wipe:

```bash
./bin/xai-oauth status
./bin/xai-oauth logout
```

GrokProvider uses that OAuth session first and only falls back to `XAI_API_KEY` (a separate metered ledger).

---

# Organic Problem Solver

Broccoli Core now supports a provider-agnostic problem solving pipeline.

```
User Goal
      |
      v
Problem Runtime
      |
      v
Evidence Collectors
      |
      v
Reasoners
      |
      v
Remediation Planner
      |
      v
Workflow Engine
      |
      v
Verification
      |
      v
Knowledge Learning
```

Future collectors should publish evidence rather than directly solving problems.

## Runtime bridges

Clipboard input is handled by a passive bridge in `runtime/clipboard/`. The bridge publishes structured command and result envelopes to the shared EventBus, and the Governor can request a restart when bridge health goes stale or the bridge stops polling.

## Managed transports

Runtime components that expose `start()`, `stop()`, and `health()` are now managed as transports. The managed set currently includes the accessibility driver, clipboard bridge, Grok provider, workflow executor, adaptive planner, knowledge graph, agent coordinator, and plugin loader, all registered with the transport registry and supervised for restart/recovery by the Governor and transport supervisor.

## Lifecycle telemetry

The runtime lifecycle now emits structured startup and shutdown events on the EventBus, including component-ready and component-stopped telemetry, so bootstrap and shutdown flows can be asserted in tests.
