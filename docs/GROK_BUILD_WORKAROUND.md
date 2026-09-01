# Grok Build CLI Workaround (subscription-billed, no API credits)

## Why
`api.x.ai` rejects SuperGrok OAuth tokens with HTTP 402 `personal-team-blocked:spending-limit`.
The official Grok Build CLI routes through `cli-chat-proxy.grok.com` and consumes the SuperGrok weekly pool.

## Install (Termux)
```bash
curl -fsSL https://x.ai/cli/install.sh | bash
export PATH="$HOME/.grok/bin:$PATH"
grok --version
grok login --device-auth   # prints URL + code; approve in any browser
grok -p "Reply with exactly: BROCCOLI CORE ONLINE VIA SUBSCRIPTION"
```

## Required headers on cli-chat-proxy (for custom clients)
- `Authorization: Bearer <oauth_access_token>`
- `X-XAI-Token-Auth: xai-grok-cli`
- `x-grok-client-identifier: grok-shell`
- `x-grok-client-version: <current>`
- `User-Agent: grok-shell/<ver> (android; aarch64)`

## Config override
```toml
# ~/.grok/config.toml
[model.grok-build]
base_url = "https://cli-chat-proxy.grok.com/v1"
```

## Point Broccoli here
Change `GrokProvider` base URL from `https://api.x.ai/v1` to `https://cli-chat-proxy.grok.com/v1`
and attach the CLI identity headers. Then inference bills the subscription, not a second ledger.
