class Task:
    def __init__(self, id, priority="NORMAL", action=None):
        self.id = id
        self.priority = priority
        self.action = action
        self.status = "queued"
