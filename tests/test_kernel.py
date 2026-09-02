from runtime.kernel import Kernel


def test_kernel_bluetooth_dry():
    k = Kernel()
    out = k.tick("turn on bluetooth", dry_run=True)
    assert out["ok"] is True
    assert out["intent"] == "toggle_bluetooth"
    assert out["schema"] in ("turn_on_bluetooth", "toggle_bluetooth")
    assert out["confidence"] >= 0.5


def test_kernel_unknown_still_ticks():
    k = Kernel()
    out = k.tick("asdf qwer", dry_run=True)
    assert out["ok"] is True
    assert out["intent"] == "unknown"
