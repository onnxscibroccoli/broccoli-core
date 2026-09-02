from runtime.embed.factory import get_embedder
from runtime.embed.local import HashingTrickEmbedder
from runtime.embed.onnx_embed import OnnxEmbedder


def test_default_embedder_is_hashing(monkeypatch, tmp_path):
    monkeypatch.delenv("BROCCOLI_ONNX_EMBED", raising=False)
    emb = get_embedder(dim=32)
    assert isinstance(emb, HashingTrickEmbedder)
    v = emb.embed("bluetooth")
    assert len(v) == 32


def test_missing_onnx_model_falls_back(monkeypatch, tmp_path):
    monkeypatch.setenv("BROCCOLI_ONNX_EMBED", str(tmp_path / "nope.onnx"))
    emb = get_embedder(dim=32)
    assert isinstance(emb, HashingTrickEmbedder)


def test_onnx_wrapper_without_runtime_is_not_usable(tmp_path):
    model = tmp_path / "toy.onnx"
    model.write_bytes(b"not-an-onnx-file")
    emb = OnnxEmbedder(model, dim=32)
    assert emb.usable is False
    assert len(emb.embed("hello")) == 32
