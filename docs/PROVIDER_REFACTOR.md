# Broccoli Core — provider refactor

## What changed

- `runtime/providers/grok.py` now hits the real xAI endpoint
  (`https://api.x.ai/v1/chat/completions`) with `XAI_API_KEY`. No more
  print-and-pray. Results land on the EventBus as `ConversationUpdated`
  and `ProviderResult`.
- `runtime/config.py` is file-backed (`~/broccoli/config.json`) with env
  overlays. Secrets stay in env, never in git.
- `runtime/plugin_loader.py` cleaned up for readability.

## Env vars

| Variable | Purpose |
|---|---|
| `XAI_API_KEY` | xAI API key (required for live Grok) |
| `GROK_API_KEY` | fallback key name |
| `XAI_API_BASE_URL` | override base URL |
| `GROK_MODEL` | model id, default `grok-4.6` |
| `BROCCOLI_CONFIG` | path to config.json |

## Unix philosophy

Each provider is a small, single-purpose module. The EventBus is the
pipeline. Compose, don't bloat.
