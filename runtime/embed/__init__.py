"""On-device embedding interfaces. Default path is stdlib-only."""

from runtime.embed.local import HashingTrickEmbedder, LocalEmbedder

__all__ = ["HashingTrickEmbedder", "LocalEmbedder"]
