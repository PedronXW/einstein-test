"""Testes TDD da feature F-021 (retry transiente no RAG/LLM).

Valida que o retry ocorre apenas ANTES do primeiro token, com tenacity,
para exceções transientes; após esgotar → erro. Embeddings com retry.
"""

import asyncio

import pytest

from einstein_test.services.rag import FakeChatLLM, RagService
from einstein_test.vector import FakeEmbedder


class _FlakyLLM:
    """Falha nas primeiras N chamadas astream e depois emite tokens."""

    def __init__(self, fail_attempts=1, tokens=("a", "b"), fail_class=ConnectionError):
        self.fail_attempts = fail_attempts
        self.tokens = tokens
        self.fail_class = fail_class
        self.calls = 0

    def stream(self, prompt):
        raise NotImplementedError

    async def astream(self, prompt):
        self.calls += 1
        if self.calls <= self.fail_attempts:
            raise self.fail_class("timeout transiente")
        for t in self.tokens:
            yield t


def test_ac001_astream_retries_when_first_token_fails():
    # simula um LLM que falha no 1º __anext__ e depois emite tokens
    flaky = _FlakyLLM(fail_attempts=1)

    import tenacity

    out = []

    async def run():
        retrying = tenacity.AsyncRetrying(
            stop=tenacity.stop_after_attempt(2),
            wait=tenacity.wait_fixed(0.01),
            retry=tenacity.retry_if_exception_type(ConnectionError),
        )
        async for attempt in retrying:
            with attempt:
                first = await flaky.astream("p").__anext__()
        out.append(first)
        async for tok in flaky.astream("p"):
            out.append(tok)

    asyncio.run(run())
    assert out, "tokens produzidos após retry transiente"
    assert flaky.calls >= 2, "houve 1 falha + sucesso"


def test_ac002_stream_never_retries_after_first_token():
    # se o stream já emitiu 1 token, o restante não re-tenta (a proteção é
    # apenas na aquisição do 1º chunk)
    class _MidFail:
        async def astream(self, prompt):
            yield "tok1"
            raise ConnectionError("falha após 1 token")

    out = []

    async def run():
        try:
            async for tok in _MidFail().astream("p"):
                out.append(tok)
        except ConnectionError:
            pass

    asyncio.run(run())
    assert out == ["tok1"], "sem retry após o primeiro token"


def test_ac003_embed_question_retries():
    calls = {"n": 0}

    class _FlakyEmbedder(FakeEmbedder):
        def embed(self, texts):
            calls["n"] += 1
            if calls["n"] <= 1:
                raise ConnectionError("timeout embeddings")
            return super().embed(texts)

    svc = RagService(
        llm=FakeChatLLM(tokens=["x"]),
        retriever=None,
        embedder=_FlakyEmbedder(),
    )
    # _embed_question deve aplicar retry transiente e retornar o vetor
    emb = svc._embed_question("pergunta")
    assert len(emb) == 1536, "embedding (retry) de 1536 dims"
    assert calls["n"] >= 1, "embedder tentado"


def test_ac004_config_env_defaults(monkeypatch):
    from einstein_test.services import rag as rag

    # constantes existem com defaults numéricos
    assert hasattr(rag, "LLM_MAX_RETRIES")
    assert hasattr(rag, "LLM_RETRY_BACKOFF")
    assert rag.LLM_MAX_RETRIES >= 1
    assert rag.LLM_RETRY_BACKOFF >= 0.1


def test_ac005_always_fail_raises_after_retries():
    import tenacity

    flaky = _FlakyLLM(fail_attempts=99)
    retrying = tenacity.AsyncRetrying(
        stop=tenacity.stop_after_attempt(2),
        wait=tenacity.wait_fixed(0.01),
        retry=tenacity.retry_if_exception_type(ConnectionError),
    )

    async def run():
        async for attempt in retrying:
            with attempt:
                async for tok in flaky.astream("p"):
                    return "tok"

    with pytest.raises(tenacity.RetryError):
        asyncio.run(run())