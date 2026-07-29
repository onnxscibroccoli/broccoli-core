from runtime.clipboard.adapter import ClipboardEventBridge
from runtime.clipboard.events import parse_result_envelope


class FakeBus:
    def __init__(self):
        self.events = []

    def publish(self, topic, payload=None, source="unknown"):
        event = {"topic": topic, "payload": payload or {}, "source": source}
        self.events.append(event)
        return event


def test_parse_result_envelope_extracts_command_and_output():
    text = """[Clipboard Agent Result]
Time: 2026-07-29 03:46:18

Command:
echo BROCCOLI_OK

Output:
BROCCOLI_OK"""
    parsed = parse_result_envelope(text)
    assert parsed["command"] == "echo BROCCOLI_OK"
    assert parsed["output"] == "BROCCOLI_OK"


def test_bridge_publishes_command_then_result_with_shared_id():
    clips = iter(
        [
            "echo BROCCOLI_OK",
            """[Clipboard Agent Result]
Time: 2026-07-29 03:46:18

Command:
echo BROCCOLI_OK

Output:
BROCCOLI_OK""",
        ]
    )

    bus = FakeBus()
    bridge = ClipboardEventBridge(
        bus,
        clipboard_get=lambda: next(clips),
        poll_interval=0.01,
    )

    bridge.poll_once()
    bridge.poll_once()

    assert [event["topic"] for event in bus.events] == [
        "CLIPBOARD_COMMAND_RECEIVED",
        "CLIPBOARD_COMMAND_RESULT",
    ]
    assert bus.events[0]["payload"]["command_id"] == bus.events[1]["payload"]["command_id"]
    assert bus.events[1]["payload"]["output"] == "BROCCOLI_OK"
