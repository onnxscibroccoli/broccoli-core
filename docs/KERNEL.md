# Kernel

The machine-sized loop. Everything else in this repo is either a transport, a log, or a leftover.

```
text → classify → resolve schema → execute steps → emit events → remember
```

## What is real

| Module | Status |
|---|---|
| `runtime/intent_schema.py` | real. library + TF-IDF index + Markov + emulator |
| `runtime/onnx_runtime.py` | keyword fallback always; ONNX session if a model file exists |
| `runtime/onyx.py` | provider loop + failover + NEED_USER / DONE / NEXT |
| `runtime/memory_vector.py` | Fernet file, mode 600, searchable |
| `runtime/cloudflare_edge.py` | client stub; disabled without creds; never blocks the phone |
| `runtime/automation/engine.py` | bluetooth / reminder / calendar / status / search_memory |
| `runtime/kernel.py` | one `tick()` that wires the above and remembers |
| `runtime/memory/vectors.py` | JSONL cosine store used by kernel remember |
| `runtime/ingest/harvest.py` | harvest JSONL → embed pipeline |
| `runtime/reminders.py` | local reminder log + notification |

## What is not real

Issues that say M1–M10 "shipped" while the files were `*_PLACEHOLDER` were lying to the next model. Those placeholders are gone.

The repo still contains megabytes of logs, backups, duplicate milestone issues, and shell scripts that rewrite each other. Do not grow that pile. Change the kernel.

## Run

```bash
python -c "from runtime.kernel import Kernel; print(Kernel().tick('turn on bluetooth'))"
```

Offline. No token. No Cloudflare.

## Remember

Every `tick()` writes the phrase to:

- encrypted kernel memory (`BROCCOLI_MEMORY_PATH` or `~/.broccoli/kernel_memory.json`)
- the embedded vector store (`BROCCOLI_VECTOR_ROOT` or `~/.broccoli/vectors`)

`search memory` resolves the `search_memory` schema and returns hybrid recall hits on the tick payload. Memory failures never fail the tick.

## Harvest to embed

```bash
python scripts/ingest_harvest.py data/harvest
```

Reads `data/harvest/*.jsonl` written by `brocc harvest` and upserts chunks into the local store. Duplicates skip on content hash.

## Reminders

`reminder.set` appends to `BROCCOLI_REMINDER_PATH` or `~/.broccoli/reminders.jsonl` and calls `termux-notification` when present. Dry-run does not write. Calendar intents are stored the same way; the engine does not claim a calendar app opened unless it actually did.
