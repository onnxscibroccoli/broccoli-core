from runtime.eventbus.service import bus

def listener(event):
    print(f"{event.topic} -> {event.payload}")

bus.subscribe("*", listener)

bus.publish(
    "runtime.started",
    {"status": "ok"},
    source="selftest"
)

print("SERVICE PASS")
