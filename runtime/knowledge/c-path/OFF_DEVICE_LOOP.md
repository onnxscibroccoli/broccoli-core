# C Path — Off-Device Loop First

Decision 2026-08-09: prioritize off-device durable workspace over on-device expansion.

## Why

- Device CPU / bandwidth / battery are hard limits
- Off-device allows concurrent LLMs, heavier tools, and parallel workers
- Results land in GitHub; device stays thin
- Build + validate off-device (emulator / cloud computer), ship ready artifacts to device

## Primary stack

- cloudflare/computer — SQLite-backed Durable Object VFS + pluggable runtimes
- cloudflare/agents — companion edge agent runtime
- GitHub as the receipt / publish surface

## Not a Termux replacement

On-device Termux + accessibility stay for local actuation. Off-device loop owns planning, multi-model compute, and durable knowledge.

## Next concrete steps

1. Spike minimal Durable Object + computer binding
2. Define result contract (what gets pushed back to repo)
3. Emulator / cloud validation path for device-bound features
4. Thin on-device consumer that pulls ready artifacts
