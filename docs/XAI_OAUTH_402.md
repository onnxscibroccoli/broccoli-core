# xAI OAuth → 402 spending-limit (SuperGrok subscription not honored)

**Status:** xAI-side billing gate. Broccoli OAuth is correct; the server rejects the session.

## What happened
Active SuperGrok subscriber, valid OAuth tokens (`oauth_present: true`, refresh present),
`./bin/broccoli ping` returns:

```json
{"code":"personal-team-blocked:spending-limit",
 "error":"You have run out of credits or need a Grok subscription. Add credits at https://grok.com/?_s=usage or upgrade at https://grok.com/supergrok."}
```

## Why this is xAI's problem, not Broccoli's
- Hermes Agent's own guide states SuperGrok OAuth uses **subscription quota, not API credits**,
  against the same `https://api.x.ai/v1` base URL.
- xAI's announcement: "use your Grok subscription directly … no API key required."
- Grok Build CLI is advertised for all SuperGrok / X Premium+ subscribers.
- Yet this account gets a 402 whose *message* tells a paying customer to buy a subscription.

Known related report: NousResearch/hermes-agent#26847 — standard SuperGrok OAuth blocked by
backend allowlist (some say Heavy-only), contradicting "every tier" docs.

## What Broccoli will and will not do
- WILL: keep OAuth-first, never auto-charge the API ledger, surface raw error bodies.
- WILL NOT: purchase API credits on your behalf. That is an explicit second purchase.

## Paths that actually bill the subscription (no API ledger)
1. **Grok Build CLI** (official, SuperGrok-gated):
   ```bash
   curl -fsSL https://x.ai/cli/install.sh | bash
   grok   # sign in with your SuperGrok account
   ```
2. **Hermes Agent** OAuth provider (`xai-oauth`) — same flow, same quota promise;
   may also 403 on standard tiers per #26847.
3. Consumer surfaces: grok.com, official Grok app.

## Escalation (user-owned)
- xAI support (attach raw 402 + this doc).
- CFPB: consumerfinance.gov/complaint
- FTC: reportfraud.ftc.gov
- ADA accommodation: company first, then ADA.gov

Full issue: broccoli-core#23.
