# Vector store (M3)

Offline, file-backed vector memory for Broccoli Core.

## Components

| Piece | Path | Role |
| --- | --- | --- |
| Embedder | `runtime/embed/local.py` | Hashing-trick vectors. Stdlib only. |
| Pipeline | `runtime/embed/pipeline.py` | Chunk → embed → incremental upsert |
| Store | `runtime/memory/vectors.py` | JSONL + cosine search |
| Hybrid recall | `runtime/memory/search.py` | Cosine + lexical bonus |
| CLI | `runtime/memory/cli.py` | `init` / `embed` / `recall` / `harvest` / `health` |
| Harvest ingest | `runtime/ingest/harvest.py` | `data/harvest/*.jsonl` → upsert |

This is an **in-process embedded store**, not a hosted database. GitHub cannot run a live DB server. The index file lives on the device (`~/.broccoli/vectors/index.jsonl`, mode 600).

## Init

```bash
python scripts/init_vector_store.py
python -m runtime.memory.cli init
python -m runtime.memory.cli embed "turn on bluetooth from settings"
python -m runtime.memory.cli recall "how do I enable bluetooth"
python scripts/ingest_harvest.py data/harvest
```

Kernel `tick()` also upserts the phrase after schema resolution. Harvest files from `brocc harvest` are incremental.

## Why hashing instead of MiniLM / FAISS / Pinecone

- Kernel and CI stay offline and Termux-safe.
- No token, no Cloudflare, no third-party embedding API by default.
- Same `embed(text) -> List[float]` contract. An ONNX embedder can replace `HashingTrickEmbedder` later without rewriting the store.

## Hosted options (not default)

If a hosted backend is needed later: Qdrant Cloud free tier, Supabase pgvector, or a container on Fly/Render. Keep the device path as the source of truth and treat cloud as an optional replica.
