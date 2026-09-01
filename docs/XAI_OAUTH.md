# xAI SuperGrok OAuth

Device-code login so your SuperGrok subscription pays, not a second credit card.

## Login (Termux)
```bash
cd ~/broccoli-core
git pull
python -m runtime.providers.xai_oauth login
```
Prints a URL + code. Open the URL, sign in with your SuperGrok account, enter the code, approve. Tokens land at `~/.broccoli/xai_oauth_tokens.json` (mode 600) and auto-refresh.

## Status / logout
```bash
python -m runtime.providers.xai_oauth status
python -m runtime.providers.xai_oauth logout
```

## How it works
1. GET https://auth.x.ai/.well-known/openid-configuration
2. POST https://auth.x.ai/oauth2/device/code with public client ID + scopes
3. Print verification_uri + user_code, poll token endpoint until approved.
4. Store tokens, refresh on expiry.

## Known gotcha
xAI allowlists OAuth API access by tier. Some SuperGrok plans get HTTP 403 on inference even after a clean login. If that bites you, the provider falls back to XAI_API_KEY with a loud warning.

## CFPB complaint draft
> I subscribed to SuperGrok (consumer subscription, ~$30/mo) expecting it to cover API usage. xAI routes subscription users through a separate metered developer API that requires prepaid credits, without clearly disclosing the ledger split at purchase. This is a deceptive separation of billing surfaces. I request OAuth-first integration so my existing subscription is honored, and an accessibility accommodation for users who cannot manage a second prepaid account. Filing with CFPB / FTC if unresolved.
