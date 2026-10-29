"""Orquestração da avaliação: por pergunta -> métricas + veredito + relatório."""

from __future__ import annotations

from dataclasses import dataclass

from einstein_test.eval.dataset import EvalQuestion
from einstein_test.eval.judge import FakeJudge, Judge, JudgeVerdict
from einstein_test.eval.metrics import hit_rate_at_1, mrr_at_k, recall_at_k


@dataclass(frozen=True)
class RetrievalMetrics:
    recall_5: float
    recall_12: float
    mrr_5: float
    hit_1: float


@dataclass
class QuestionResult:
    question: EvalQuestion
    metrics: RetrievalMetrics
    verdict: JudgeVerdict
    similarity: float
    answer: str
    ttft: float
    latency: float
    robustness_ok: bool = True


@dataclass
class EvalReport:
    results: list[QuestionResult]

    def aggregates(self) -> dict[str, float]:
        if not self.results:
            return {}
        return {
            "recall@5": _mean(r.metrics.recall_5 for r in self.results),
            "recall@12": _mean(r.metrics.recall_12 for r in self.results),
            "mrr@5": _mean(r.metrics.mrr_5 for r in self.results),
            "hit@1": _mean(r.metrics.hit_1 for r in self.results),
            "correctness": _mean(r.verdict.correctness for r in self.results),
            "faithfulness": _mean(r.verdict.faithfulness for r in self.results),
            "coverage": _mean(r.verdict.coverage for r in self.results),
            "similarity": _mean(r.similarity for r in self.results),
            "latency": _mean(r.latency for r in self.results),
            "robustness": _mean(float(r.robustness_ok) for r in self.results),
        }

    def to_dict(self) -> dict:
        return {
            "results": [_result_to_dict(r) for r in self.results],
            "aggregates": self.aggregates(),
        }


def _mean(values) -> float:
    vals = list(values)
    return round(sum(vals) / len(vals), 4) if vals else 0.0


def _result_to_dict(r: QuestionResult) -> dict:
    return {
        "question": {
            "id": r.question.id,
            "question": r.question.question,
            "expected_files": list(r.question.expected_files),
            "domain": r.question.domain,
            "edge": r.question.edge,
        },
        "metrics": {
            "recall_5": r.metrics.recall_5,
            "recall_12": r.metrics.recall_12,
            "mrr_5": r.metrics.mrr_5,
            "hit_1": r.metrics.hit_1,
        },
        "verdict": {
            "correctness": r.verdict.correctness,
            "faithfulness": r.verdict.faithfulness,
            "coverage": r.verdict.coverage,
            "rationale": r.verdict.rationale,
        },
        "similarity": r.similarity,
        "answer": r.answer,
        "ttft": r.ttft,
        "latency": r.latency,
        "robustness_ok": r.robustness_ok,
    }


def run_eval(
    questions: list[EvalQuestion],
    *,
    search_fn,
    answer_fn,
    similarity_fn,
    judge: Judge | None = None,
    file_id_of=None,
    limit: int | None = None,
) -> EvalReport:
    """Roda a avaliação por pergunta.

    - `search_fn(question) -> list[int]`: arquivos ordenados por relevância (ids).
    - `answer_fn(question) -> (answer, context, ttft, latency)`.
    - `similarity_fn(answer, gold) -> float`.
    - `file_id_of(question, name) -> int`: id do arquivo do corpus (default:
      índice na lista de `expected_files` + 1).
    """
    judge = judge or FakeJudge()
    if file_id_of is None:
        file_id_of = lambda q, name: list(q.expected_files).index(name) + 1
    if limit is not None:
        questions = questions[:limit]

    results: list[QuestionResult] = []
    for q in questions:
        expected = {file_id_of(q, name) for name in q.expected_files}
        ranked = search_fn(q)
        answer, context, ttft, latency = answer_fn(q)

        metrics = RetrievalMetrics(
            recall_5=recall_at_k(ranked, expected, 5),
            recall_12=recall_at_k(ranked, expected, 12),
            mrr_5=mrr_at_k(ranked, expected, 5),
            hit_1=hit_rate_at_1(ranked, expected),
        )
        verdict = judge.judge(
            question=q.question, gold_answer=q.gold_answer, answer=answer, context=context
        )
        robustness_ok = not (q.edge == "no_context" and answer.strip())
        results.append(
            QuestionResult(
                question=q,
                metrics=metrics,
                verdict=verdict,
                similarity=similarity_fn(answer, q.gold_answer),
                answer=answer,
                ttft=ttft,
                latency=latency,
                robustness_ok=robustness_ok,
            )
        )
    return EvalReport(results=results)