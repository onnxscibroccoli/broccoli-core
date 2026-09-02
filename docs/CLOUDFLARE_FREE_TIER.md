# Cloudflare Free-Tier Resource Map

Broccoli uses Cloudflare's free surface as a remote brain that never bills
the user. Every call degrades gracefully to on-device execution.

## What's free (as of 2026-09)

| Service | Free limit | Broccoli use |
|---|---|---|
| Workers | 100k req/day, 50 subreq/req, 128MB, 10ms CPU | schema synthesis endpoint, emulator host |
| KV | 100k reads/day, 1k writes/day, 1GB | intent cache, session state |
| D1 | 5M reads/day, 100k writes/day, 5GB | **daily limits enforced since 2026-09-01** — use for cold metadata only, fall back on limit errors |
| R2 | 10GB, 1M Class A / 10M Class B /mo, free egress | encrypted memory backup, model blobs |
| Workers AI | 10,000 Neurons/day shared | tiny intent classifier, embeddings |
| Vectorize | 30M query dims/mo, 5M storage dims | remote vector search fallback |

## Env vars

```
CF_ACCOUNT_ID=...
CF_API_TOKEN=...
CF_KV_NAMESPACE=...
CF_D1_DATABASE=...
CF_R2_BUCKET=...
CF_WORKER_URL=https://broccoli.<sub>.workers.dev
CF_AI_MODEL=@cf/qwen/qwen1.5-0.5b-chat
```

## Rule

Remote is an accelerator, never a dependency. If Cloudflare is down, rate-
limited, or unconfigured, Broccoli runs entirely on-device. The user's intent
is never blocked on a third party's uptime.
