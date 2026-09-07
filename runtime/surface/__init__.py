"""Provider-agnostic execution surface.

Core talks to a VirtualSurface. Adapters own package names, launch
intents, and provider UI. This package must not import Grok, ChatGPT,
or Gemini selectors.
"""
from runtime.surface.protocol import (
    SurfaceError,
    SurfaceEvent,
    SurfaceState,
    VirtualSurface,
)
from runtime.surface.memory import MemorySurface

__all__ = [
    "SurfaceError",
    "SurfaceEvent",
    "SurfaceState",
    "VirtualSurface",
    "MemorySurface",
]
