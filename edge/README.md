# broccoli-edge — free Cloudflare compute for Broccoli Core

A tiny Worker on Cloudflare's **permanent free tier**:

- 100,000 requests/day
- 10 ms CPU/request, 128 MB memory
- 1 GB KV, 100k reads/day, 1k writes/day
- 10,000 Workers AI Neurons/day (optional, for real embeddings later)
- 10 GB R2, zero egress (encrypted blob sync later)

## Routes

| Route | Purpose |
|---|---|
| `GET /health` | Liveness |
| `POST /embed` | 64-dim deterministic hash embedding (no model, no Neurons) |
| `POST /infer` | Keyword intent classifier (bluetooth, reminder, calendar, memory) |
| `POST /sync` | Store encrypted payload in KV (30-day TTL) |
| `GET /sync/:key` | Retrieve |

## Deploy (~2 minutes, one time)

```bash
npm i -g wrangler
wrangler login
npm run kv:create   # paste the two IDs into wrangler.toml
npm run deploy
```

```bash
export BROCCOLI_EDGE_URL=https://broccoli-edge.<subdomain>.workers.dev
```

## Privacy invariant

Nothing is plaintext-identifiable by default. Payloads must be Fernet-encrypted *before* they hit `/sync`. The Worker is a dumb encrypted mailbox, not a reader.
