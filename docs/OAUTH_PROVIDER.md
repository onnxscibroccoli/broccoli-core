# OAuth Provider — SuperGrok First, Credits Never

## Philosophy
If you pay for SuperGrok, you should not be forced to buy API credits to use the same models. The subscription *is* the access. OAuth is the correct, honest path. API keys are the fallback for CI/CD and headless environments only.

## Flow (Device Code Grant)
1. `broccoli xai login` (or `python -m src.providers.xai_oauth login`)
2. Browser opens `https://auth.x.ai/oauth2/device/code` verification page.
3. User signs in with their X / grok.com account (the one with SuperGrok).
4. Tokens stored at `~/.broccoli/xai_oauth_tokens.json` (mode 600).
5. All inference requests use `Authorization: Bearer <access_token>` against `https://api.x.ai/v1`.
6. Refresh tokens rotate automatically on 401 / expiry.

## Constants
| Item | Value |
|------|-------|
| Issuer | `https://auth.x.ai` |
| Device code URL | `https://auth.x.ai/oauth2/device/code` |
| Token URL | `https://auth.x.ai/oauth2/token` |
| Client ID | `b1a00492-073a-47ea-816f-4c329264a828` |
| Scope | `openid profile email offline_access grok-cli:access api:access` |
| Inference base | `https://api.x.ai/v1` |

## Credential Priority
1. Active OAuth session (always wins)
2. Explicit session key passed in-code
3. `XAI_API_KEY` env (only if no OAuth token present)
4. Error: "No active session. Run `broccoli xai login`."

## Headless / Termux
```bash
python -m src.providers.xai_oauth login --device
# prints URL + code; open on another device, enter code
```

## Fallback Behavior
If OAuth returns 403 "no active Grok subscription", the provider surfaces a clear error and suggests checking that the X account email matches the grok.com account. It does **not** silently fall back to charging credits.

## Security
- Tokens never logged.
- File permissions locked to 600.
- Refresh tokens rotated; old ones invalidated server-side.
- Logout deletes the store.

## Why This Exists
See issue #17. SuperGrok subscribers were being pushed into a separate prepaid-credit ledger — a dark pattern. This provider makes the subscription the single source of truth.
