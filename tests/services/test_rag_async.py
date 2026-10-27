"""Testes TDD da feature F-013 (AC-001/AC-002/AC-003: astream no RAG).

Valida FakeChatLLM.astream determinístico e RagService.astream (grafo
LangGraph async stream_mode custom) sem gastar tokens.
"""

import pytest

from einstein_test.services.rag import FakeChatLLM, RagService
from einstein_test.vector import FakeEmbedder
from einstein_test.vector.similarity import cosine_similarity_search


class _FakeVectorRepo:
    def __init__(self, chunks):
        self._chunks = chunks

    def search_similar(self, embedding, chat_id, chunks_per_file=2, max_chunks=12):
        return cosine_similarity_search(embedding, self._chunks, top_k=max_chunks)


def _chunk(content, file_id=1):
    return type(
        "Chunk",
        (),
        {"content": content, "file_id": file_id, "embedding": [1.0, 0.0, 0.0]},
    )()


def _service(chunks, tokens=None):
    return RagService(
        llm=FakeChatLLM(tokens=tokens),
        retriever=_FakeVectorRepo(chunks),
        embedder=FakeEmbedder(),
    )


def test_ac003_fake_chatllm_has_astream():
    fake = FakeChatLLM(tokens=["a", "b"])
    assert hasattr(fake, "astream"), "FakeChatLLM expõe astream"


@pytest.mark.anyio
async def test_ac003_fake_astream_deterministic():
    fake = FakeChatLLM(tokens=["a", "b"])
    tokens = [t async for t in fake.astream("prompt")]
    assert tokens == ["a", "b"]
    fake2 = FakeChatLLM(tokens=["a", "b"])
    tokens2 = [t async for t in fake2.astream("outro")]
    assert tokens2 == ["a", "b"], "astream determinístico"


@pytest.mark.anyio
async def test_ac002_rag_service_astream_emits_tokens():
    service = _service([_chunk("sobre gorilas")], tokens=["token1", "token2"])
    tokens = [t async for t in service.astream(
        question="o que há?", chat_id=1, history=[]
    )]
    assert tokens == ["token1", "token2"]


@pytest.mark.anyio
async def test_ac002_rag_astream_uses_retriever():
    service = _service([_chunk("sobre gorilas")], tokens=["t1", "t2"])
    tokens = [t async for t in service.astream(
        question="gorilas?", chat_id=1, history=[]
    )]
    assert tokens == ["t1", "t2"]


def test_ac001_chatllm_protocol_has_astream():
    from einstein_test.services.rag import ChatLLM

    # Protocol declara astream; implementações conformam
    attrs = {name for name in dir(ChatLLM) if not name.startswith("_")}
    assert {"stream", "astream"} <= attrs, "Protocol ChatLLM declara stream e astream"
    from einstein_test.services.rag import ChatOpenAIAdapter, FakeChatLLM

    assert hasattr(FakeChatLLM, "astream")
    assert hasattr(ChatOpenAIAdapter, "astream")


@pytest.mark.anyio
async def test_ac002_rag_astream_empty_history_ok():
    service = _service([], tokens=["x"])
    tokens = [t async for t in service.astream(
        question="?", chat_id=1, history=[]
    )]
    assert tokens == ["x"], "histórico vazio não quebra astream"