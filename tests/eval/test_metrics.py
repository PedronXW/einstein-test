"""Testes TDD da F-038 — AC-001: métricas de retrieval."""

import pytest

from einstein_test.eval.metrics import hit_rate_at_1, mrr_at_k, recall_at_k


def test_ac001_recall_at_k_basic():
    assert recall_at_k(ranked_files=[1, 2, 3, 4], expected_files={2, 4}, k=4) == pytest.approx(1.0)
    assert recall_at_k(ranked_files=[1, 2, 3, 4], expected_files={2, 4}, k=2) == pytest.approx(0.5)
    assert recall_at_k(ranked_files=[1, 2, 3, 4], expected_files={9}, k=4) == pytest.approx(0.0)


def test_ac001_recall_at_k_edge_cases():
    assert recall_at_k(ranked_files=[], expected_files=set(), k=5) == pytest.approx(0.0)
    assert recall_at_k(ranked_files=[1, 2], expected_files={1}, k=100) == pytest.approx(1.0)
    assert recall_at_k(ranked_files=[], expected_files={1}, k=5) == pytest.approx(0.0)


def test_ac001_mrr_at_k():
    assert mrr_at_k(ranked_files=[9, 2, 3], expected_files={2}, k=5) == pytest.approx(0.5)
    assert mrr_at_k(ranked_files=[1, 2, 3], expected_files={2}, k=1) == pytest.approx(0.0)
    assert mrr_at_k(ranked_files=[2, 1], expected_files={4}, k=5) == pytest.approx(0.0)
    assert mrr_at_k(ranked_files=[], expected_files={1}, k=5) == pytest.approx(0.0)


def test_ac001_hit_rate_at_1():
    assert hit_rate_at_1(ranked_files=[3, 1], expected_files={3}) == pytest.approx(1.0)
    assert hit_rate_at_1(ranked_files=[1, 3], expected_files={3}) == pytest.approx(0.0)
    assert hit_rate_at_1(ranked_files=[], expected_files={3}) == pytest.approx(0.0)


def test_ac001_recall_mrr_with_k_zero():
    assert recall_at_k(ranked_files=[1, 2], expected_files={1}, k=0) == pytest.approx(0.0)
    assert mrr_at_k(ranked_files=[1, 2], expected_files={1}, k=0) == pytest.approx(0.0)