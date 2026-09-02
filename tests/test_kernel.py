from runtime.kernel import Kernel


def test_kernel_bluetooth_dry():
    k = Kernel()
    out = k.tick("turn on bluetooth", dry_run=True)
    assert out["ok"] is True
    assert out["schema"] == "turn_on_bluetooth"
    assert out["confidence"] >= 0.5
    assert out["schema_run"]["status"] == "dry"
    assert "bluetooth.on" in out["schema_run"]["steps"]
    assert "action" not in out  # no second actuator


def test_kernel_unknown_still_ticks():
    k = Kernel()
    out = k.tick("asdf qwer", dry_run=True)
    assert out["ok"] is True
    assert out["intent"] == "unknown"
