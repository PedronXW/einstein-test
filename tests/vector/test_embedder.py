"""Testes TDD da feature F-010 (AC-001: Embedder).

Valida o Protocol Embedder, o OpenAIEmbedder (config via .env/OPENAI_*,
model cohere/embed-v4.0, base url OpenAI-compatível, dim 1024) e o
FakeEmbedder determinístico.
"""

import pytest

from einstein_test.vector import Embedder, FakeEmbedder, OpenAIEmbedder


def test_ac001_embedder_is_protocol():
    assert hasattr(Embedder, "embed"), "Embedder expõe embed(texts) -> list[list[float]]"


def test_ac001_openai_embedder_model_and_dim():
    assert OpenAIEmbedder.model == "cohere/embed-v4.0"
    assert OpenAIEmbedder.dim == 1024


def test_ac001_openai_embedder_base_url_default():
    assert OpenAIEmbedder.base_url == "https://spillway.ensinoeinstein.com/openai/v1"


def test_ac001_openai_embedder_reads_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://spillway.ensinoeinstein.com/openai/v1")
    monkeypatch.setenv("OPENAI_MODEL", "cohere/embed-v4.0")
    monkeypatch.delenv("OPENAI_EMBEDDING_DIM", raising=False)
    emb = OpenAIEmbedder()
    assert emb.api_key == "sk-test"
    assert emb.model == "cohere/embed-v4.0"
    assert emb.base_url == "https://spillway.ensinoeinstein.com/openai/v1"
    assert emb.dim == 1024


def test_ac001_openai_embedder_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        OpenAIEmbedder()


def test_ac001_fake_embedder_deterministic():
    emb = FakeEmbedder()
    a = emb.embed(["olá mundo"])
    b = emb.embed(["olá mundo"])
    assert a == b, "FakeEmbedder determinístico para o mesmo texto"
    assert len(a) == 1
    assert len(a[0]) == 1024, "vetor de 1024 dims (cohere/embed-v4.0)"


def test_ac001_fake_embedder_distinct_texts():
    emb = FakeEmbedder()
    a = emb.embed(["um texto"])
    b = emb.embed(["outro texto"])
    assert a != b, "textos distintos geram vetores distintos"


def test_ac001_fake_embedder_batch():
    emb = FakeEmbedder()
    vecs = emb.embed(["a", "b", "c"])
    assert len(vecs) == 3
    assert all(len(v) == 1024 for v in vecs)


def test_ac001_fake_embedder_dims_are_floats():
    emb = FakeEmbedder()
    vec = emb.embed(["x"])[0]
    assert all(isinstance(v, float) for v in vec)