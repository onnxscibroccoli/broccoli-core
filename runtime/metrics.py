class Metrics:
    def __init__(self):
        self.counters = {}
    def increment(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1
    def get(self, key):
        return self.counters.get(key, 0)
