"""Módulo de vetorização: embedder, extração, chunking e repositório pgvector."""

from einstein_test.vector.chunker import TextChunker
from einstein_test.vector.embedder import Embedder, FakeEmbedder, OpenAIEmbedder
from einstein_test.vector.extractor import TEXT_EXTENSIONS, TextExtractor
from einstein_test.vector.repository import VectorRepository, VectorRepositorySQLAlchemy

_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    """Retorna o embedder configurado (OpenAI por padrão; fake nos testes)."""
    global _embedder
    if _embedder is None:
        _embedder = OpenAIEmbedder()
    return _embedder


def set_embedder(embedder: Embedder) -> None:
    global _embedder
    _embedder = embedder


__all__ = [
    "Embedder",
    "FakeEmbedder",
    "OpenAIEmbedder",
    "TEXT_EXTENSIONS",
    "TextChunker",
    "TextExtractor",
    "VectorRepository",
    "VectorRepositorySQLAlchemy",
    "get_embedder",
    "set_embedder",
]