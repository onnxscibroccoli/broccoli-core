"""
Compatibility bridge.

Legacy modules importing event_bus.py are redirected
to the canonical runtime.eventbus implementation.
"""

from runtime.eventbus import EventBus, Event

_default_bus = EventBus()


def get_event_bus():
    return _default_bus


def publish(topic, payload=None, source="legacy"):
    return _default_bus.publish(
        topic,
        payload or {},
        source=source
    )


def subscribe(topic, callback):
    return _default_bus.subscribe(
        topic,
        callback
    )
