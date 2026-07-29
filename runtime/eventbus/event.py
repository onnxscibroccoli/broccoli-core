class Event:
    def __init__(self, topic, payload=None, source="unknown"):
        self.topic = topic
        self.payload = payload or {}
        self.source = source

    def get(self, key, default=None):
        return self.payload.get(key, default)

    def __getitem__(self, key):
        return self.payload[key]

    def __contains__(self, key):
        return key in self.payload

    def items(self):
        return self.payload.items()

    def keys(self):
        return self.payload.keys()

    def values(self):
        return self.payload.values()

    def __bool__(self):
        return bool(self.payload)

    def __repr__(self):
        return (
            f"Event(topic={self.topic!r}, "
            f"payload={self.payload!r}, "
            f"source={self.source!r})"
        )
