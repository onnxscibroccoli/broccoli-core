# Cloudflare Edge — free compute for Broccoli Core

## The inversion, extended to the cloud

The phone runs the hot path (Termux, ONNX, encrypted store). Cloudflare runs the always-on, heavy, or shared path — for **free**, with **zero egress**, and with **zero data sold**. Same free tier advertisers get. Pointed at the user.

## Free resources

| Resource | Free allowance | Use |
|---|---|---|
| Workers | 100k req/day, 10ms CPU, 128MB | broccoli-edge: /embed /infer /sync |
| KV | 1GB, 100k reads/day, 1k writes/day | encrypted payload relay |
| Workers AI | 10k Neurons/day | optional real embeddings (BGE) |
| R2 | 10GB, 0 egress | encrypted model-weight cache, blob sync |
| D1 | 5GB, 5M reads/day | structured cross-account memory index |
| GitHub Actions | unlimited (public repo) | CI for Worker + Python runtime |

## Deploy

```bash
cd edge
npm i -g wrangler
wrangler login
npm run kv:create
# paste IDs into wrangler.toml
npm run deploy
export BROCCOLI_EDGE_URL=https://broccoli-edge.<sub>.workers.dev
```

## Privacy

Client-side Fernet encryption before `/sync`. The edge is a dumb mailbox. See issue #48.
