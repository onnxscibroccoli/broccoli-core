from runtime.eventbus import EventBus

bus = EventBus()

def printer(event):
    print(f"[EVENT] {event.topic} from {event.source}")
    print(event.payload)

bus.subscribe("*", printer)

bus.publish(
    "repo.status",
    {
        "branch":"alpha-testing",
        "ahead":0,
        "changes":0
    },
    source="selftest"
)

print("PASS")
