# Deploy from device (no local workerd)

## One-time secrets (GitHub repo)

Settings → Secrets and variables → Actions:

| Secret | Value |
|--------|--------|
| CLOUDFLARE_API_TOKEN | Token with Edit Cloudflare Workers |
| CLOUDFLARE_ACCOUNT_ID | Dashboard → Workers → Account ID |

Create token: Cloudflare dashboard → My Profile → API Tokens →
Create Token → template "Edit Cloudflare Workers".

## Trigger from Termux

```bash
gh workflow run deploy-do-spike.yml --ref c-off-device-loop
gh run watch
Heredoc got cut off. Finish cleanly:

```bash
cd "$HOME/broccoli-core"
git checkout c-off-device-loop

# rewrite DEPLOY.md fully
cat > runtime/off_device/spike/DEPLOY.md << 'EOF'
# Deploy from device (no local workerd)

## One-time secrets (GitHub repo)

Settings → Secrets and variables → Actions:

| Secret | Value |
|--------|--------|
| CLOUDFLARE_API_TOKEN | Token with Edit Cloudflare Workers |
| CLOUDFLARE_ACCOUNT_ID | Dashboard → Workers → Account ID |

Create token: Cloudflare dashboard → My Profile → API Tokens → Create Token → template "Edit Cloudflare Workers".

## Trigger from Termux

```bash
gh workflow run deploy-do-spike.yml --ref c-off-device-loop
gh run watch
```

Or push any change under runtime/off_device/spike/.

## After deploy

Worker name: broccoli-do-spike
URL shape: https://broccoli-do-spike.YOUR_SUBDOMAIN.workers.dev

```bash
export SPIKE_URL="https://broccoli-do-spike.YOUR_SUBDOMAIN.workers.dev"
curl -sS "$SPIKE_URL/"
curl -sS -X POST "$SPIKE_URL/write" -H 'content-type: application/json' \
  -d '{"path":"hello.md","content":"# from CI\n"}'
curl -sS "$SPIKE_URL/read?path=hello.md"
```

Device stays thin: HTTP client only. Linux CI owns wrangler/workerd.
