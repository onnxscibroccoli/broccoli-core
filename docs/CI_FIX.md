# CI fix: requirements.txt + expanded offline matrix

## What broke

Runs 5–7 failed at `actions/setup-python` with:

```
No file in ... matched to [**/requirements.txt or **/pyproject.toml]
```

`pyproject.toml` existed, but the cache step's `hashFiles` glob was empty at
eval time and the explicit `requirements.txt` the cache key referenced was
missing. setup-python's `cache: pip` then hard-failed instead of degrading.

## Fix

1. Added a real `requirements.txt` (stdlib-only baseline; heavy deps stay in
   `pyproject.toml` optional-dependencies).
2. Pointed both `actions/cache` and `setup-python` `cache-dependency-path` at
   `requirements.txt`.
3. Expanded the offline pytest matrix to cover the new ONNX / memory / ingest /
   vector / automation surfaces — all zero-network, zero-secret.

## Why this matters for the vision

The encrypted memory, ONNX intent classifier, ingest adapters, and vector index
are the backbone of personal data sovereignty. If CI can't even *test* them
headless, the whole agentic loop is unproven. This fix makes every push a
verifiable, reproducible build of the offline core.
