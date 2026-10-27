"""Similaridade vetorial (cosine) — usada na busca RAG.

O pgvector suporta o operador `<=>` no PostgreSQL. Para testes com SQLite
(que não implementa o operador), calculamos a similaridade em Python.
"""

import math

from einstein_test.models.file_chunk import FileChunk


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosseno entre dois vetores; 0.0 se algum for nulo."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def cosine_similarity_search(
    query: list[float],
    rows: list[FileChunk],
    top_k: int = 4,
) -> list[FileChunk]:
    """Retorna os `top_k` chunks mais similares ao vetor de consulta."""
    ranked = sorted(
        rows,
        key=lambda chunk: cosine_similarity(query, list(chunk.embedding)),
        reverse=True,
    )
    return ranked[:top_k]


def per_file_top_k_search(
    query: list[float],
    rows: list[FileChunk],
    chunks_per_file: int = 2,
    max_chunks: int = 12,
) -> list[FileChunk]:
    """Retorna os chunks mais similares por arquivo.

    Para cada arquivo do chat, mantém os `chunks_per_file` chunks mais
    similares; depois reordena globalmente por similaridade e trunca em
    `max_chunks` — priorizando os arquivos mais relevantes.
    """
    by_file: dict[int, list[FileChunk]] = {}
    for chunk in rows:
        by_file.setdefault(chunk.file_id, []).append(chunk)

    per_file: list[tuple[float, FileChunk]] = []
    for file_id, file_chunks in by_file.items():
        file_ranked = sorted(
            file_chunks,
            key=lambda c: cosine_similarity(query, list(c.embedding)),
            reverse=True,
        )
        for chunk in file_ranked[:chunks_per_file]:
            per_file.append(
                (cosine_similarity(query, list(chunk.embedding)), chunk)
            )

    per_file.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in per_file[:max_chunks]]