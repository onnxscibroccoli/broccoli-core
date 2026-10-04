"""Minimal recall/embed entry points used by scripts and tests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from runtime.embed.local import HashingTrickEmbedder
from runtime.embed.pipeline import EmbedPipeline
from runtime.memory.search import HybridSearch
from runtime.memory.vectors import VectorStore


def default_store_root() -> Path:
    return Path.home() / ".broccoli" / "vectors"


def build_stack(root: Path | None = None) -> Dict[str, Any]:
    store_root = Path(root) if root else default_store_root()
    store = VectorStore(store_root)
    embedder = HashingTrickEmbedder()
    return {
        "store": store,
        "embedder": embedder,
        "pipeline": EmbedPipeline(store, embedder),
        "search": HybridSearch(store, embedder),
        "root": store_root,
    }


def embed_text(text: str, root: Path | None = None, source: str = "cli") -> Dict[str, Any]:
    stack = build_stack(root)
    result = stack["pipeline"].ingest(text, source=source, kind="note")
    result["root"] = str(stack["root"])
    result["documents"] = stack["store"].count()
    return result


def recall(query: str, root: Path | None = None, top_k: int = 5) -> List[Dict[str, Any]]:
    stack = build_stack(root)
    return stack["search"].recall(query, top_k=top_k)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="broccoli-vector")
    parser.add_argument("--root", default="", help="Vector store directory")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="Create the local store directory")
    p_embed = sub.add_parser("embed", help="Embed text into the store")
    p_embed.add_argument("text")
    p_embed.add_argument("--source", default="cli")
    p_recall = sub.add_parser("recall", help="Semantic recall")
    p_recall.add_argument("query")
    p_recall.add_argument("--top-k", type=int, default=5)
    sub.add_parser("health")
    args = parser.parse_args(argv)
    root = Path(args.root) if args.root else None
    if args.cmd == "init":
        stack = build_stack(root)
        stack["store"].flush()
        print(json.dumps(stack["store"].health()))
        return 0
    if args.cmd == "embed":
        print(json.dumps(embed_text(args.text, root=root, source=args.source)))
        return 0
    if args.cmd == "recall":
        print(json.dumps(recall(args.query, root=root, top_k=args.top_k), indent=2))
        return 0
    if args.cmd == "health":
        print(json.dumps(build_stack(root)["store"].health()))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
