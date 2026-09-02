"""On-device embedding interfaces. Default path is stdlib-only."""

from runtime.embed.factory import get_embedder
from runtime.embed.local import HashingTrickEmbedder, LocalEmbedder

__all__ = ["HashingTrickEmbedder", "LocalEmbedder", "get_embedder"]
