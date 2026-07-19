from typing import Callable, Dict, List, Any

class EventBus:
    def __init__(self):
        # Map of topic -> list of subscriber callbacks
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(self, topic: str, callback: Callable[[Any], None]) -> None:
        """Registers a callback for a specific event topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        if callback not in self._subscribers[topic]:
            self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable[[Any], None]) -> None:
        """Removes a callback from a specific event topic."""
        if topic in self._subscribers and callback in self._subscribers[topic]:
            self._subscribers[topic].remove(callback)

    def publish(self, topic: str, payload: Any = None) -> None:
        """Dispatches an event payload to all subscribers of the topic."""
        if topic in self._subscribers:
            for callback in self._subscribers[topic]:
                try:
                    callback(payload)
                except Exception as e:
                    # TODO: Wire this into the EventJournal
                    print(f"[EventBus] Error in subscriber for {topic}: {e}")
