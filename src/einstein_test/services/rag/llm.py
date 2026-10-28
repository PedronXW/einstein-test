"""LLM para o RAG: Protocol, fakes e adapters (OpenAI-compatível).

Contém `ChatLLM` (Protocol), `FakeChatLLM` (determinístico p/ testes) e
`ChatOpenAIAdapter` (client real com retry transiente no primeiro token), além
das constantes de configuração e do helper `allowed_models()`.
"""

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any, Protocol

from tenacity import (
    AsyncRetrying,
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from einstein_test.settings import get_settings

DEFAULT_CHAT_MODEL = "azure/gpt-5-mini"
DEFAULT_BASE_URL = "https://spillway.ensinoeinstein.com/openai/v1"

LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
LLM_RETRY_BACKOFF = float(os.getenv("LLM_RETRY_BACKOFF", "1"))

DEFAULT_ALLOWED_MODELS = "azure/gpt-5-mini,azure/gpt-6-luna"


def allowed_models() -> list[str]:
    """Modelos de LLM permitidos, lidos do env `ALLOWED_MODELS`.

    Lido por request (call-time) para refletir mudanças do operador; usa o
    default quando ausente/vazio.
    """
    from dotenv import load_dotenv

    load_dotenv()
    raw = os.getenv("ALLOWED_MODELS") or DEFAULT_ALLOWED_MODELS
    return [m.strip() for m in raw.split(",") if m.strip()]


class ChatLLM(Protocol):
    def stream(self, prompt: str) -> Iterator[str]: ...
    def astream(self, prompt: str) -> AsyncIterator[str]: ...


class FakeChatLLM:
    """LLM determinístico para testes (emite tokens fixos)."""

    def __init__(self, tokens: list[str] | None = None) -> None:
        self.tokens = tokens or ["token1", "token2"]

    def stream(self, prompt: str) -> Iterator[str]:
        yield from self.tokens

    async def astream(self, prompt: str) -> AsyncIterator[str]:
        for token in self.tokens:
            yield token


def _is_transient(exc: BaseException) -> bool:
    """Exceções re-tentáveis (rede/storage/timeout/provedor temporário)."""
    return isinstance(exc, (ConnectionError, TimeoutError, OSError))


def _retrying() -> AsyncRetrying:
    return AsyncRetrying(
        stop=stop_after_attempt(LLM_MAX_RETRIES),
        wait=wait_exponential(multiplier=LLM_RETRY_BACKOFF, min=0.05, max=5),
        retry=retry_if_exception(_is_transient),
        reraise=True,
    )


def _retrying_sync() -> Retrying:
    return Retrying(
        stop=stop_after_attempt(LLM_MAX_RETRIES),
        wait=wait_exponential(multiplier=LLM_RETRY_BACKOFF, min=0.05, max=5),
        retry=retry_if_exception(_is_transient),
        reraise=True,
    )


class ChatOpenAIAdapter:
    """ChatLLM real via langchain-openai ChatOpenAI (azure/gpt-5-mini)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        cfg = get_settings()
        self.api_key = api_key or cfg.openai_api_key
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY não configurada (defina no .env)")
        from langchain_openai import ChatOpenAI

        self.model = model or cfg.openai_chat_model
        self.base_url = base_url or cfg.openai_base_url
        self._llm = ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            streaming=True,
        )

    def stream(self, prompt: str) -> Iterator[str]:
        # retry transiente na aquisição do 1º token (não depois)
        it = iter(self._llm.stream(prompt))
        while True:
            try:
                first = next(it)
                break
            except StopIteration:
                return
            except Exception as exc:  # noqa: BLE001
                if not _is_transient(exc):
                    raise
                for attempt in _retrying_sync():
                    with attempt:
                        it = iter(self._llm.stream(prompt))
                        first = next(it)
                break
        yield (first.content or "")
        for c in it:
            yield (c.content or "")

    async def astream(self, prompt: str) -> AsyncIterator[str]:
        # retry transiente apenas ANTES do primeiro token
        it: Any = None
        first: Any = None
        try:
            async for attempt in _retrying():
                with attempt:
                    it = self._llm.astream(prompt).__aiter__()
                    first = await it.__anext__()
        except StopAsyncIteration:
            return
        yield (getattr(first, "content", None) or "")
        async for chunk in it:
            yield (getattr(chunk, "content", None) or "")


__all__ = [
    "ChatLLM",
    "FakeChatLLM",
    "ChatOpenAIAdapter",
    "allowed_models",
    "DEFAULT_CHAT_MODEL",
    "DEFAULT_BASE_URL",
    "LLM_MAX_RETRIES",
    "LLM_RETRY_BACKOFF",
]