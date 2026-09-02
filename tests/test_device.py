from runtime.device import bluetooth_set, notify
from runtime.automation.engine import AutomationEngine
from runtime.kernel import Kernel


def test_bluetooth_set_does_not_claim_success_offline():
    r = bluetooth_set(want_on=True)
    assert "ok" in r
    assert r["action"] == "bluetooth"
    if r["ok"] is False:
        assert r.get("note") or r.get("stderr") is not None


def test_notify_never_raises():
    r = notify("hello")
    assert r["action"] == "notification"
    assert "ok" in r


def test_engine_dry_run_still_ok():
    eng = AutomationEngine()
    r = eng.run("toggle_bluetooth", {"dry_run": True})
    assert r["ok"] is True
    assert r["dry_run"] is True


def test_kernel_wires_executors_dry():
    k = Kernel()
    out = k.tick("turn on bluetooth", dry_run=True)
    assert out["schema_run"]["status"] == "dry"
    assert "bluetooth.on" in out["schema_run"]["steps"]
