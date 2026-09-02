from runtime.reminders import ReminderStore, parse_when
from runtime.automation.engine import AutomationEngine


def test_parse_when_clock():
    assert parse_when("remind me at 8am") == "08:00"
    assert parse_when("take meds at 8:30 pm") == "20:30"
    assert parse_when("tomorrow") == "tomorrow"
    assert parse_when("no time here") is None


def test_reminder_store_persists(tmp_path, monkeypatch):
    monkeypatch.setenv("BROCCOLI_REMINDER_PATH", str(tmp_path / "rem.jsonl"))
    store = ReminderStore()
    rec = store.add("take morning medication at 8am")
    assert rec["when"] == "08:00"
    rows = store.list()
    assert len(rows) == 1
    assert "medication" in rows[0]["text"]


def test_engine_reminder_dry_run_does_not_write(tmp_path, monkeypatch):
    monkeypatch.setenv("BROCCOLI_REMINDER_PATH", str(tmp_path / "rem.jsonl"))
    eng = AutomationEngine()
    r = eng.run("reminder.set", {"text": "meds at 9am", "dry_run": True})
    assert r["ok"] is True
    assert r["dry_run"] is True
    assert not (tmp_path / "rem.jsonl").exists()


def test_engine_reminder_persists(tmp_path, monkeypatch):
    monkeypatch.setenv("BROCCOLI_REMINDER_PATH", str(tmp_path / "rem.jsonl"))
    eng = AutomationEngine()
    r = eng.run("reminder.set", {"text": "meds at 9am"})
    assert r["ok"] is True
    assert r["stub"] is False
    assert (tmp_path / "rem.jsonl").exists()
