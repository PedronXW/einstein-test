"""Serviço RAG: orquestra retrieve+generate e expõe a factory global.

`RagService` embrulha um LLM (default `ChatOpenAIAdapter`), um retriever
(session-based) e um embedder, expondo `stream`/`astream` via grafo LangGraph.
A factory (`get_rag_service`) cria o adapter por usuário com o modelo
escolhido (F-022); o embedder permanece compartilhado.
"""

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any, Callable

from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

from einstein_test.services.rag.graph import build_graph, build_graph_async, build_prompt
from einstein_test.services.rag.llm import (
    LLM_MAX_RETRIES,
    LLM_RETRY_BACKOFF,
    ChatOpenAIAdapter,
    ChatLLM,
    _is_transient,
)
from einstein_test.vector import Embedder, get_embedder
from einstein_test.vector.repository import VectorRepository


class RagService:
    def __init__(
        self,
        llm: ChatLLM | None = None,
        retriever: VectorRepository | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self.llm: ChatLLM = llm or ChatOpenAIAdapter()
        self.retriever = retriever
        self.embedder: Embedder = embedder or get_embedder()
        self._graph = None
        self._graph_async = None

    def _embed_question(self, question: str) -> list[float]:
        """Gera o embedding da pergunta com retry transiente (tenacity)."""
        retrying = Retrying(
            stop=stop_after_attempt(LLM_MAX_RETRIES),
            wait=wait_exponential(multiplier=LLM_RETRY_BACKOFF, min=0.05, max=5),
            retry=retry_if_exception(_is_transient),
            reraise=True,
        )
        for attempt in retrying:
            with attempt:
                return self.embedder.embed([question])[0]
        raise RuntimeError("embedding falhou após retries")

    @property
    def graph(self) -> Any:
        if self.retriever is None:
            raise RuntimeError("retriever não configurado")
        if self._graph is None:
            self._graph = build_graph(
                llm=self.llm, retriever=self.retriever, embedder=self.embedder
            )
        return self._graph

    @property
    def graph_async(self) -> Any:
        if self.retriever is None:
            raise RuntimeError("retriever não configurado")
        if self._graph_async is None:
            self._graph_async = build_graph_async(
                llm=self.llm, retriever=self.retriever, embedder=self.embedder
            )
        return self._graph_async

    def stream(
        self,
        question: str,
        chat_id: int,
        history: list[str],
    ) -> Iterator[str]:
        """Gera a resposta RAG em streaming (tokens) via grafo LangGraph."""
        for chunk in self.graph.stream(
            {
                "question": question,
                "history": history,
                "chat_id": chat_id,
            },
            stream_mode="custom",
        ):
            yield chunk

    async def astream(
        self,
        question: str,
        chat_id: int,
        history: list[str],
    ) -> AsyncIterator[str]:
        """Gera a resposta RAG em streaming async (tokens) via grafo."""
        async for chunk in self.graph_async.astream(
            {
                "question": question,
                "history": history,
                "chat_id": chat_id,
            },
            stream_mode="custom",
        ):
            yield chunk

    def _build_prompt(
        self,
        question: str,
        chunks: list[Any],
        history: list[str],
    ) -> str:
        return build_prompt(question, chunks, history)

    def _generate_answer(
        self,
        question: str,
        chat_id: int,
        history: list[str],
    ) -> str:
        return "".join(self.stream(question=question, chat_id=chat_id, history=history))


_rag_factory: Callable[..., RagService] | None = None
_shared_embedder: Embedder | None = None


def get_rag_service(
    retriever: VectorRepository, *, model: str | None = None
) -> RagService:
    """Retorna o serviço RAG para o retriever da sessão atual.

    O `ChatOpenAIAdapter` é criado **por usuário** com o `model` escolhido (ou
    o default do ambiente quando `model` é None) — não há mais singleton do
    LLM. O `Embedder` permanece compartilhado (client HTTP de embeddings).
    """
    global _shared_embedder
    if _rag_factory is not None:
        kwargs = {"model": model} if model is not None else {}
        return _rag_factory(retriever=retriever, **kwargs)
    if _shared_embedder is None:
        _shared_embedder = get_embedder()
    return RagService(
        llm=ChatOpenAIAdapter(model=model),
        retriever=retriever,
        embedder=_shared_embedder,
    )


def set_rag_factory(factory: Callable[..., RagService]) -> None:
    global _rag_factory
    _rag_factory = factory


def reset_rag_factory() -> None:
    global _rag_factory
    _rag_factory = None
    global _shared_embedder
    _shared_embedder = None


__all__ = ["RagService", "get_rag_service", "set_rag_factory", "reset_rag_factory"]