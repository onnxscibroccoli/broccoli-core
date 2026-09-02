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
| `runtime/automation/engine.py` | bluetooth / reminder / calendar / status |
| `runtime/kernel.py` | one `tick()` that wires the above |

## What is not real

Issues that say M1–M10 "shipped" while the files were `*_PLACEHOLDER` were lying to the next model. Those placeholders are gone.

The repo still contains megabytes of logs, backups, duplicate milestone issues, and shell scripts that rewrite each other. Do not grow that pile. Change the kernel.

## Run

```bash
python -c "from runtime.kernel import Kernel; print(Kernel().tick('turn on bluetooth'))"
```

Offline. No token. No Cloudflare.
