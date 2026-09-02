# Grok Build CLI Workaround (subscription-billed, no API credits)

## Why
`api.x.ai` rejects SuperGrok OAuth tokens with HTTP 402 `personal-team-blocked:spending-limit`.
The official Grok Build CLI routes through `cli-chat-proxy.grok.com` and consumes the SuperGrok weekly pool.

Confirmed 2026-09-01 on Termux aarch64: `grok 1.0.13` + device-code login returned
`BROCCOLI CORE ONLINE VIA SUBSCRIPTION`.

## Install (Termux)
```bash
curl -fsSL https://x.ai/cli/install.sh | bash
export PATH="$HOME/.grok/bin:$PATH"
grok --version
grok login --device-auth
grok -p "Reply with exactly: BROCCOLI CORE ONLINE VIA SUBSCRIPTION"
```

## Broccoli transport order
1. Official `grok -p` if `~/.grok/bin/grok` and `~/.grok/auth.json` exist.
2. HTTP OAuth / API key to `XAI_BASE_URL` or `api.x.ai` (last resort; 402s SuperGrok).

```bash
cd "$HOME/broccoli-core"
git pull origin main
export PATH="$HOME/.grok/bin:$PATH"
./bin/broccoli status
./bin/broccoli ping
./bin/broccoli ask say hello from broccoli via grok cli
```

Force the old HTTP path only for debugging:
```bash
BROCCOLI_FORCE_HTTP=1 ./bin/broccoli ping
```
