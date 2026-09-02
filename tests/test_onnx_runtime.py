"""Offline tests for the REAL ONNX integration."""
from runtime.onnx_runtime import OnnxIntentClassifier, KNOWN_INTENTS


def test_fallback_classifies_bluetooth():
    c = OnnxIntentClassifier()
    r = c.classify("turn on my bluetooth")
    assert r["intent"] == "bluetooth.on"
    assert r["source"] == "keyword"
    assert r["score"] == 1.0


def test_fallback_classifies_bluetooth_off():
    c = OnnxIntentClassifier()
    r = c.classify("turn off bluetooth")
    assert r["intent"] == "bluetooth.off"


def test_fallback_classifies_reminder():
    c = OnnxIntentClassifier()
    r = c.classify("remind me to take my meds")
    assert r["intent"] == "set_reminder"


def test_fallback_unknown():
    c = OnnxIntentClassifier()
    r = c.classify("asdf qwer zxcv")
    assert r["intent"] == "unknown"
    assert r["score"] == 0.0


def test_health_reports_no_model():
    c = OnnxIntentClassifier()
    h = c.health()
    assert h["model_loaded"] is False
    assert h["fallback_rules"] >= 5
    assert "toggle_bluetooth" in KNOWN_INTENTS


def test_empty_text():
    c = OnnxIntentClassifier()
    r = c.classify("   ")
    assert r["intent"] == "unknown"
