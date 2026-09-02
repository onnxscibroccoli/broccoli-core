"""Compatibility shim.

This directory used to hide runtime/event_bus.py. The real bus is
runtime.eventbus.bus.EventBus. Re-export it so `from runtime.event_bus import EventBus` works.
"""
from runtime.eventbus.bus import EventBus
from runtime.eventbus.event import Event

__all__ = ["EventBus", "Event"]
