"""Grok-facing evidence collection.

Grok proposes. Broccoli collects and verifies. This package does not grant
execution authority and does not boot the governor stack.
"""

from runtime.grok.evidence import SCHEMA_VERSION, collect_evidence

__all__ = ["SCHEMA_VERSION", "collect_evidence"]
