# Broccoli Edge (Cloudflare Worker)

Free-tier remote brain for Broccoli Core. Zero cost, zero data sold.

## What it does

- `/ingest` — store encrypted conversation records (KV, 30-day TTL)
- `/search` — substring search over stored records
- `/emulator/trial` — dry-run a schema, persist pass/fail
- `/ai/embed` — BGE embeddings via Workers AI (10k neurons/day free)
- `/ai/classify` — tiny intent classifier via Qwen 0.5B
- `/stats` — KV key count

## Deploy

```bash
cd edge
npm i -g wrangler
wrangler login
# edit wrangler.toml: set account_id, KV id, D1 id
wrangler kv:namespace create "KV_NS"
wrangler d1 create broccoli-meta
wrangler vectorize create broccoli-vectors --dimensions=384 --metric=cosine
wrangler deploy
```

## Free tier (2026-09)

| Service | Free limit |
|---|---|
| Workers | 100k req/day, 10ms CPU, 128MB, 50 subreq/req |
| KV | 100k reads/day, 1k writes/day, 1GB |
| D1 | 5M reads/day, 100k writes/day (enforced daily since 2026-09-01) |
| Vectorize | 30M queried dims/mo, 5M stored dims |
| Workers AI | 10k neurons/day (or 10k tokens/day text+embed) |
| R2 | 10GB, 1M Class A / 10M Class B /mo, free egress |

## Rule

Remote is an accelerator, never a dependency. If the edge is down or
rate-limited, Broccoli runs entirely on-device. The user's intent is
never blocked on a third party's uptime.
