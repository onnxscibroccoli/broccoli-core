from constants import STATE_RUNNING, STATE_RECOVERING
from event_bus import EventBus

class Governor:
    def __init__(self, bus: EventBus, state):
        self.bus = bus
        self.state = state
        self.bus.subscribe("TICK", self.on_tick)
        self.bus.subscribe("AccessibilityCaptureReady", self.on_accessibility)

    def on_tick(self, _):
        if self.state.current == STATE_RUNNING:
            self.bus.publish("GOVERNOR_HEARTBEAT")

    def on_accessibility(self, payload):
        if payload and payload.get("primary_action"):
            print("Governor: Primary action (send) ready")
        if payload and payload.get("next_editable"):
            print("Governor: Input field ready")

    def recover(self):
        print("Governor: Recovery started")
        self.state.transition(STATE_RECOVERING)
        self.bus.publish("GovernorRecoveryStarted")
