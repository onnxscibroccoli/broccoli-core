from inspect import getsource

from runtime.surface import MemorySurface
from runtime.surface import protocol
from runtime.surface.protocol import ALLOWED_OPS, SESSION_STATES


def test_memory_surface_happy_path():
    s = MemorySurface(session="ready")
    assert s.create("demo-provider").ok
    assert s.focus().ok
    assert s.input("hello").ok
    assert s.submit().ok
    obs = s.observe()
    assert obs.ok
    assert obs.details["submitted"] == 1
    st = s.inspect()
    assert st.attached is True
    assert st.provider_id == "demo-provider"
    assert s.detach().ok
    assert s.destroy().ok
    assert s.input("nope").ok is False
    assert s.input("nope").code == "destroyed"


def test_unauthenticated_does_not_accept_input():
    s = MemorySurface(session="unauthenticated")
    s.create("any")
    s.focus()
    ev = s.input("secret")
    assert ev.ok is False
    assert ev.code == "unauthenticated"
    rec = s.recover()
    assert rec.ok is False
    assert rec.code == "unauthenticated"


def test_core_contract_has_no_provider_brand():
    src = getsource(protocol).lower()
    for brand in ("ai.x.grok", "chatgpt", "gemini", "openai"):
        assert brand not in src
    for op in (
        "create",
        "attach",
        "inspect",
        "focus",
        "input",
        "submit",
        "observe",
        "recover",
        "detach",
        "destroy",
    ):
        assert op in ALLOWED_OPS
    assert "unauthenticated" in SESSION_STATES


def test_unavailable_is_explicit():
    s = MemorySurface(session="unavailable")
    ev = s.create("x")
    assert ev.ok is False
    assert ev.code == "unavailable"
