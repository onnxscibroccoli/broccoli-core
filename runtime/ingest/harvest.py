"""Turn harvest JSONL / adapter records into vector memory.

Offline. Incremental. Deduped by content hash in the store.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from runtime.embed.pipeline import EmbedPipeline
from runtime.ingest.adapters import ingest as adapt_ingest
from runtime.memory.cli import build_stack

PathLike = Union[str, Path]


def _text_of(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, dict):
        return str(item).strip()
    for key in ("text", "content", "tail", "line"):
        val = item.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def records_from_object(obj: Any, *, source: str = "harvest") -> List[Dict[str, Any]]:
    """Normalize harvest blobs and adapter output into pipeline items."""
    items: List[Dict[str, Any]] = []
    if obj is None:
        return items
    if isinstance(obj, list):
        for i, row in enumerate(obj):
            text = _text_of(row)
            if not text:
                continue
            meta = {"index": i}
            if isinstance(row, dict):
                if row.get("provider"):
                    meta["provider"] = row.get("provider")
                if row.get("role"):
                    meta["role"] = row.get("role")
            items.append(
                {
                    "text": text,
                    "source": source,
                    "kind": "chat",
                    "meta": meta,
                }
            )
        return items
    if not isinstance(obj, dict):
        text = _text_of(obj)
        return [{"text": text, "source": source, "kind": "chat", "meta": {}}] if text else []

    thread_id = str(obj.get("thread_id") or obj.get("id") or "harvest")
    lines = obj.get("lines")
    if isinstance(lines, list) and lines:
        for i, line in enumerate(lines):
            text = _text_of(line)
            if not text:
                continue
            items.append(
                {
                    "text": text,
                    "source": source,
                    "kind": "chat",
                    "doc_id": f"{thread_id}:{i}",
                    "meta": {"thread_id": thread_id},
                }
            )
        return items

    text = _text_of(obj)
    if text:
        items.append(
            {
                "text": text,
                "source": source,
                "kind": "chat",
                "doc_id": thread_id,
                "meta": {"thread_id": thread_id},
            }
        )
    return items


def load_jsonl(path: Path) -> List[Any]:
    rows: List[Any] = []
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return rows
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            rows.append({"text": line})
    return rows


def harvest_paths(root: PathLike) -> List[Path]:
    base = Path(root)
    if base.is_file():
        return [base]
    if not base.is_dir():
        return []
    files = sorted(base.glob("*.jsonl"))
    latest = base / "latest.json"
    if latest.is_file():
        files.append(latest)
    return files


def embed_harvest(
    harvest_root: PathLike,
    *,
    store_root: Optional[PathLike] = None,
    source: str = "harvest",
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    stack = build_stack(Path(store_root) if store_root else None)
    pipeline: EmbedPipeline = stack["pipeline"]
    files = harvest_paths(harvest_root)
    totals = {"ok": True, "files": 0, "added": 0, "skipped": 0, "docs": 0, "paths": []}
    for path in files:
        totals["files"] += 1
        totals["paths"].append(str(path))
        if path.suffix == ".json" and path.name == "latest.json":
            try:
                blob = json.loads(path.read_text(encoding="utf-8"))
                objects = [blob]
            except Exception:
                objects = []
        else:
            objects = load_jsonl(path)
        for obj in objects:
            if provider:
                normalized = adapt_ingest(provider, obj)
                batch = records_from_object(normalized, source=source)
            else:
                batch = records_from_object(obj, source=source)
            result = pipeline.ingest_many(batch)
            totals["added"] += int(result.get("added") or 0)
            totals["skipped"] += int(result.get("skipped") or 0)
            totals["docs"] += int(result.get("docs") or 0)
    totals["documents"] = stack["store"].count()
    totals["root"] = str(stack["root"])
    return totals


def embed_records(records: Iterable[Dict[str, Any]], store_root: Optional[PathLike] = None) -> Dict[str, Any]:
    stack = build_stack(Path(store_root) if store_root else None)
    result = stack["pipeline"].ingest_many(records)
    result["documents"] = stack["store"].count()
    result["root"] = str(stack["root"])
    return result
