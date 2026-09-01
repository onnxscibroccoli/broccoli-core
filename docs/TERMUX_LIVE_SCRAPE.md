# Termux Live Scrape Mode

Goal: terminal reads grok.com chat DOM directly, no API.

## Tier 1 — text browser (zero deps)
```bash
pkg install lynx
lynx -dump https://grok.com
# or
pkg install w3m
w3m -dump https://grok.com
```
Good for static pages. Fails on JS-rendered chat.

## Tier 2 — headless Chromium (CDP, no X11)
```bash
pkg install x11-repo
pkg install chromium
pip install playwright-core websocket-client
# launch with --no-sandbox, connect via CDP on :9222
```
See: github.com/Jobians/playwright-termux or github.com/aidoctor654-sys/constrained-browser-automation

## Tier 3 — AdGuard userscript injection
AdGuard for Android: Settings → Filtering → Userscripts.
Inject a script on grok.com that POSTs the chat container innerText to http://127.0.0.1:8787/ingest.
Termux runs a tiny listener that polls /ingest and feeds Broccoli.
AdGuard Extra is preinstalled on premium; custom scripts may need Tampermonkey-style GM APIs.

## Resource guard
- Cap concurrent Chromium instances to 1.
- Kill browser on idle > 60s.
- Fall back to lynx if memory > 70%.
- Split long scrapes into chunks; outsource heavy parsing to a cheap worker if device is constrained.
