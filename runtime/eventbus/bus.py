import logging
from collections import defaultdict
from threading import Lock
from .event import Event

class EventBus:
    def __init__(self):
        self._subs = defaultdict(list)
        self._lock = Lock()
        self._log = logging.getLogger("EventBus")

    def subscribe(self, topic, callback):
        with self._lock:
            self._subs[topic].append(callback)
            self._log.info("Subscribed %s -> %s",
                           topic,
                           getattr(callback, "__name__", repr(callback)))

    def emit(self, topic, payload=None, source="legacy"):
        return self.publish(
            topic,
            payload or {},
            source=source
        )

    def publish(self, topic, payload=None, source="unknown"):
        if payload is None:
            payload = {}

        event = Event(topic=topic,
                      payload=payload,
                      source=source)

        callbacks = []

        with self._lock:
            callbacks.extend(self._subs.get(topic, []))
            callbacks.extend(self._subs.get("*", []))

        for cb in callbacks:
            try:
                cb(event)
            except Exception:
                self._log.exception(
                    "Subscriber failed for %s",
                    topic
                )

        return event

    def topics(self):
        with self._lock:
            return list(self._subs.keys())
