# Principles review (2026-09-01)

External review claimed Broccoli shipped a commercial, provider-locked, manual token flow.

## What was actually wrong
The *xAI product split* is commercial: `api.x.ai` bills a Personal Team credit ledger; Grok Build CLI bills the SuperGrok weekly pool. Broccoli did not invent that gate. Pointing Termux at the CLI was the accessible path for a SuperGrok subscriber who cannot buy a second ledger.

## What the review got right
- `ProviderManager` was a stub (`print`, no failover).
- Defaulting to Grok is a hint, not a contract. Offline `EchoProvider` now exists for tests and degraded mode.
- Server-side GitHub write should not require the phone. Public-repo GitHub Actions uses the built-in `GITHUB_TOKEN`. No extra paid runner.
- Broccoli-owned OAuth files still need refresh-on-use (CLI already refreshes `~/.grok/auth.json`). Do not make a human paste a new key every session.

## What the review got wrong
- Event bus already exists. `GrokProvider` publishes `ProviderConnected`, `ProviderResult`, `ProviderError`. Manager now also publishes `ProviderRegistered`, `ProviderUsed`, `ProviderFailover`.
- Accessibility-first on this device is Termux + device-code + no extra purchase. Console billing was the exclusionary path.
- Provider-agnostic does not mean "never call Grok." It means Grok is one registered transport.

## Next autonomous work (no human unless auth expires)
1. CI green on Actions.
2. Manager failover: grok_cli → echo (and later other providers).
3. Structured health snapshot on every `broccoli status`.
4. Keep secrets off the public issue tracker.
