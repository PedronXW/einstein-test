"""Testes TDD da F-038 — AC-003: runner de geração (rag_service.astream)."""

import asyncio
from dataclasses import dataclass

from einstein_test.eval.generation import GenerationResult, run_generation
from einstein_test.services.rag import RagService
from einstein_test.services.rag.llm import FakeChatLLM
from einstein_test.vector import FakeEmbedder


@dataclass
class _FakeChunk:
    file_id: int
    content: str


class _FakeRetriever:
    def __init__(self, chunks):
        self.chunks = chunks

    def search_similar(self, embedding, chat_id, chunks_per_file, max_chunks):
        return self.chunks


def _run(coro):
    return asyncio.run(coro)


def test_ac003_generation_collects_answer_and_perf():
    llm = FakeChatLLM(tokens=["primeiro ", "segundo"])
    retriever = _FakeRetriever([
        _FakeChunk(file_id=1, content="chunk a"),
        _FakeChunk(file_id=2, content="chunk b"),
    ])
    embedder = FakeEmbedder(dim=8)
    rag = RagService(llm=llm, retriever=retriever, embedder=embedder)

    res: GenerationResult = _run(run_generation(
        question="pergunta",
        chat_id=42,
        rag_service=rag,
        retriever=retriever,
        embedder=embedder,
        history=[],
    ))

    assert res.answer == "primeiro segundo"
    assert res.context == ["chunk a", "chunk b"]
    assert res.n_tokens == 2
    assert res.ttft >= 0
    assert res.latency >= res.ttft
    assert "pergunta" in res.prompt