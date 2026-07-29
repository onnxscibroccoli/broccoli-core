from runtime.state import RuntimeState
from runtime.eventbus import EventBus
class Governor:
    def __init__(self, bus: EventBus, state):
        self.bus = bus
        self.state = state
        self.bus.subscribe("TICK", self.on_tick)
    def on_tick(self, _):
        if self.state.current == "RUNNING":
            self.bus.publish("GOVERNOR_HEARTBEAT")
