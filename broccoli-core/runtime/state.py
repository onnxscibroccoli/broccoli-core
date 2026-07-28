STATE_INITIALIZING = "INITIALIZING"
STATE_RUNNING = "RUNNING"
STATE_RECOVERING = "RECOVERING"
STATE_STOPPING = "STOPPING"
STATE_STOPPED = "STOPPED"

class RuntimeState:
    def __init__(self):
        self.current = STATE_INITIALIZING
    def transition(self, new_state):
        print(f"State: {self.current} → {new_state}")
        self.current = new_state
