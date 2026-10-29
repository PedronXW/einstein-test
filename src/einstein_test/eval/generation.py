"""Runner de geração: resposta via rag_service.astream + contexto + perf."""

from __future__ import annotations

import time
from dataclasses import dataclass

from einstein_test.services.rag.graph import CHUNKS_PER_FILE, MAX_CHUNKS, build_prompt
from einstein_test.services.rag.service import RagService
from einstein_test.vector import Embedder, VectorRepository


@dataclass
class GenerationResult:
    answer: str
    context: list[str]
    ttft: float
    latency: float
    n_tokens: int
    prompt: str = ""


async def run_generation(
    *,
    question: str,
    chat_id: int,
    rag_service: RagService,
    retriever: VectorRepository,
    embedder: Embedder,
    history: list[str] | None = None,
) -> GenerationResult:
    """Coleta resposta real (rag_service.astream), contexto e perf (TTFT/latência)."""
    history = history or []
    query_embedding = embedder.embed([question])[0]
    chunks = retriever.search_similar(
        embedding=query_embedding,
        chat_id=chat_id,
        chunks_per_file=CHUNKS_PER_FILE,
        max_chunks=MAX_CHUNKS,
    ) or []
    context = [c.content for c in chunks]
    prompt = build_prompt(question, chunks, history)

    start = time.perf_counter()
    pieces: list[str] = []
    ttft: float | None = None
    async for token in rag_service.astream(question=question, chat_id=chat_id, history=history):
        if ttft is None:
            ttft = time.perf_counter() - start
        pieces.append(token)
    latency = time.perf_counter() - start

    return GenerationResult(
        answer="".join(pieces),
        context=context,
        ttft=ttft or 0.0,
        latency=latency,
        n_tokens=len(pieces),
        prompt=prompt,
    )