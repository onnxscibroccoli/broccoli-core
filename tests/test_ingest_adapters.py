"""Offline tests for chat history ingest adapters."""
from runtime.ingest.adapters import ingest, GrokAdapter, ChatGPTAdapter


def test_grok_adapter_list():
    raw = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    out = ingest("grok", raw)
    assert len(out) == 2
    assert out[0]["provider"] == "grok"
    assert out[0]["role"] == "user"
    assert out[1]["content"] == "hello"


def test_chatgpt_adapter_mapping():
    raw = {
        "conversations": [{
            "mapping": {
                "n1": {"message": {"author": {"role": "user"}, "content": {"parts": ["yo"]}, "create_time": 1.0}},
                "n2": {"message": {"author": {"role": "assistant"}, "content": {"parts": ["sup"]}, "create_time": 2.0}},
            }
        }]
    }
    out = ingest("chatgpt", raw)
    assert len(out) == 2
    assert out[0]["provider"] == "chatgpt"
    assert out[0]["content"] == "yo"


def test_unknown_provider_falls_back_to_web():
    out = ingest("totally-new-ai", [{"role": "user", "text": "x"}])
    assert out[0]["provider"] == "totally-new-ai"
