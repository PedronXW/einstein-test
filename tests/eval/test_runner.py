"""Testes TDD da F-038 — AC-006: runner agrega métricas + similaridade + robustez."""

from einstein_test.eval.dataset import EvalQuestion
from einstein_test.eval.judge import FakeJudge
from einstein_test.eval.runner import run_eval
from einstein_test.vector import FakeEmbedder


def _q(qid, expected, edge=""):
    return EvalQuestion(
        id=qid,
        question=f"pergunta {qid}",
        expected_files=tuple(expected),
        gold_answer=f"gold {qid}",
        edge=edge,
    )


def _search_fn_ranked():
    """Devolve os expected_files na ordem exata (retrieval perfeito)."""

    def fn(q):
        return list(range(1, len(q.expected_files) + 1))

    return fn


def _answer_fn_canned(questions):
    answers = {q.id: q.gold_answer for q in questions}
    contexts = {q.id: [f"ctx {q.id}"] for q in questions}

    def fn(q):
        a = "IGNORAR-fabricado" if q.edge == "no_context" else answers[q.id]
        return a, contexts[q.id], 0.05, 0.10

    return fn


def test_ac006_runner_aggregates_metrics_and_similarity():
    questions = [_q("q1", ["a.md"]), _q("q2", ["a.md", "b.md"])]
    embedder = FakeEmbedder(dim=8)
    report = run_eval(
        questions,
        search_fn=_search_fn_ranked(),
        answer_fn=_answer_fn_canned(questions),
        judge=FakeJudge(),
        similarity_fn=lambda a, g: embedder_sim(embedder, a, g),
        limit=None,
    )
    assert len(report.results) == 2
    q1, q2 = report.results
    assert q1.metrics.recall_5 == 1.0 and q1.metrics.mrr_5 == 1.0 and q1.metrics.hit_1 == 1.0
    # gold == answer -> similaridade alta
    assert q1.similarity > 0.99
    assert q2.metrics.recall_5 == 1.0
    agg = report.aggregates()
    assert agg["recall@5"] > 0.99


def test_ac006_robustness_no_context_flagged():
    questions = [_q("q-noctx", ["a.md"], edge="no_context")]
    report = run_eval(
        questions,
        search_fn=_search_fn_ranked(),
        answer_fn=_answer_fn_canned(questions),
        judge=FakeJudge(),
        similarity_fn=lambda a, g: 0.5,
        limit=None,
    )
    r = report.results[0]
    assert r.robustness_ok is False, (
        "pergunta fora do corpus com resposta fabricada -> robustez falha"
    )


def test_ac006_limit_respects_subset():
    questions = [_q("q1", ["a.md"]), _q("q2", ["a.md"])]
    report = run_eval(
        questions,
        search_fn=_search_fn_ranked(),
        answer_fn=_answer_fn_canned(questions),
        judge=FakeJudge(),
        similarity_fn=lambda a, g: 0.5,
        limit=1,
    )
    assert len(report.results) == 1


def embedder_sim(embedder, a, g):
    from einstein_test.vector.similarity import cosine_similarity

    return cosine_similarity(embedder.embed([a])[0], embedder.embed([g])[0])