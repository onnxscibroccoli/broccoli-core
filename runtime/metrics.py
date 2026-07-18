class Metrics:
    def __init__(self):
        self.cycles = 0
    def increment(self, key):
        if key == "cycle": self.cycles += 1
