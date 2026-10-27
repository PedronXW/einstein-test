"""Embedder: gera embeddings a partir de textos."""

import hashlib
import os
import struct
from typing import Protocol

from dotenv import load_dotenv

DEFAULT_MODEL = "cohere/embed-v4.0"
DEFAULT_DIM = 1536
DEFAULT_BASE_URL = "https://spillway.ensinoeinstein.com/openai/v1"


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder:
    """Embedder real via endpoint OpenAI-compatível (config em .env)."""

    model = DEFAULT_MODEL
    dim = DEFAULT_DIM
    base_url = DEFAULT_BASE_URL

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        dim: int | None = None,
        base_url: str | None = None,
    ) -> None:
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY não configurada (defina no .env)"
            )
        self.model = model or os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        self.dim = dim or int(os.getenv("OPENAI_EMBEDDING_DIM", DEFAULT_DIM))
        self.base_url = base_url or os.getenv(
            "OPENAI_BASE_URL", DEFAULT_BASE_URL
        )
        from openai import OpenAI

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self.model, input=texts)
        vectors = [item.embedding for item in response.data]
        if any(len(v) != self.dim for v in vectors):
            raise ValueError(
                f"embedding com dimensão inesperada (esperado {self.dim})"
            )
        return vectors


class FakeEmbedder:
    """Embedder determinístico (testes): hash do texto -> vetor de `dim` floats."""

    dim = DEFAULT_DIM

    def __init__(self, dim: int = DEFAULT_DIM) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            seed = struct.unpack("<Q", digest[:8])[0]
            vectors.append([_unit(seed, i) for i in range(self.dim)])
        return vectors


def _unit(seed: int, index: int) -> float:
    """Float pseudo-aleatório determinístico no intervalo [-1, 1]."""
    h = hashlib.sha256(
        seed.to_bytes(8, "little") + index.to_bytes(4, "little")
    ).digest()
    return (struct.unpack("<Q", h[:8])[0] % 2000000) / 1000000 - 1.0