"""Watch-Me-Do catalog: record, search, replay.

User-facing analogue of Automate / Watch Me Do.
Stores semantic steps. Never stores password/OTP/token values.
Replay of a cataloged task the user marked authorized
does not ask a second gate.
"""
from runtime.watchme.catalog import WatchCatalog
from runtime.watchme.record import WatchSession, redact_value

__all__ = ["WatchCatalog", "WatchSession", "redact_value"]
