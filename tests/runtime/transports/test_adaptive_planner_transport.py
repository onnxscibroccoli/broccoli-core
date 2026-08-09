from runtime.planner.adaptive import AdaptivePlanner

class FakeBus:
    def subscribe(self, *args, **kwargs):
        pass

    def publish(self, *args, **kwargs):
        pass

def test_adaptive_planner_transport_lifecycle():
    planner = AdaptivePlanner(bus=FakeBus())

    assert planner.health()["running"] is False

    planner.start()
    assert planner.health()["running"] is True

    planner.stop()
    assert planner.health()["running"] is False
