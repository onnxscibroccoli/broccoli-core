# Production path (Termux)

OAuth tokens live at `~/.broccoli/xai_oauth_tokens.json` and are never committed.

```bash
cd "$HOME/broccoli-core"
git pull origin main
chmod +x bin/broccoli bin/xai-oauth

./bin/broccoli status
./bin/broccoli ping
./bin/broccoli ask "Summarize the current Broccoli Core runtime in 5 bullets."
```

`broccoli` only boots GrokProvider + EventBus. It does not start accessibility,
clipboard scraping, or the Governor. That is intentional: those stay supervised
transports and must not block a live Grok round-trip.

Auth order inside GrokProvider:

1. OAuth session from `~/.broccoli/xai_oauth_tokens.json`
2. Fallback `XAI_API_KEY` (separate metered ledger)
