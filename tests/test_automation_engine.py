"""Offline tests for the agentic automation engine."""
from runtime.automation.engine import AutomationEngine


def test_bluetooth_dry_run():
    eng = AutomationEngine()
    r = eng.run("toggle_bluetooth", {"dry_run": True})
    assert r["ok"] is True
    assert r["action"] == "bluetooth"
    assert r["dry_run"] is True


def test_unknown_intent():
    eng = AutomationEngine()
    r = eng.run("fly_to_moon")
    assert r["ok"] is False
    assert "no action" in r["error"]


def test_status():
    eng = AutomationEngine()
    r = eng.run("report_status")
    assert r["ok"] is True
    assert "online" in r["message"].lower()


def test_health_lists_intents():
    eng = AutomationEngine()
    h = eng.health()
    assert "toggle_bluetooth" in h["registered_intents"]
    assert "set_reminder" in h["registered_intents"]
