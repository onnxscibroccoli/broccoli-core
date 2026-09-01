# Draft: message to xAI support

**To:** xAI Support (via grok.com / console.x.ai in-product help)
**Re:** SuperGrok OAuth rejected by api.x.ai with deceptive 402

I hold an active SuperGrok subscription. I completed xAI's documented OAuth
device-code flow (accounts.x.ai). Tokens are valid and refreshing. The first
inference request to https://api.x.ai/v1/chat/completions returned:

  HTTP 402  code: personal-team-blocked:spending-limit
  error: "You have run out of credits or need a Grok subscription. Add credits
  at https://grok.com/?_s=usage or upgrade at https://grok.com/supergrok."

Your own documentation (Hermes Agent OAuth guide, Grok-Hermes announcement,
Grok Build CLI announcement) states SuperGrok OAuth uses the subscription
quota and requires no API credits, and is available on every tier. The error
message tells a paying subscriber to purchase a subscription they already hold.
That is misleading.

Please either:
1. Honor my SuperGrok OAuth quota on api.x.ai, or
2. State honestly which tiers are allowlisted and stop advertising "every tier."

Raw response body and account identifiers available on request.
Account / team: dceee33b-dad5-4e00-a410-795c833de66a

---
If xAI does not rectify within 15 days, I will file with:
- CFPB: consumerfinance.gov/complaint
- FTC: reportfraud.ftc.gov
- ADA accommodation request via ADA.gov if applicable
