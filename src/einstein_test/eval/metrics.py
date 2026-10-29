"""Métricas de retrieval da avaliação (funções puras e testáveis)."""

from __future__ import annotations


def recall_at_k(ranked_files: list[int], expected_files: set[int], k: int) -> float:
    """Fração dos arquivos esperados recuperados no top-k."""
    if not expected_files:
        return 0.0
    top = set(ranked_files[:k])
    return len(top & expected_files) / len(expected_files)


def mrr_at_k(ranked_files: list[int], expected_files: set[int], k: int) -> float:
    """Reciprocal rank do 1º arquivo esperado no top-k (0 se ausente)."""
    for i, fid in enumerate(ranked_files[:k], start=1):
        if fid in expected_files:
            return 1.0 / i
    return 0.0


def hit_rate_at_1(ranked_files: list[int], expected_files: set[int]) -> float:
    """1.0 se o arquivo esperado está na 1ª posição, senão 0."""
    if not ranked_files:
        return 0.0
    return 1.0 if ranked_files[0] in expected_files else 0.0