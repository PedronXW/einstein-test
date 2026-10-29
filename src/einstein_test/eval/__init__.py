"""Pacote de avaliação do RAG (F-038).

Ferramenta para medir assertividade e características de IA: retrieval
(recall@k, MRR), assertividade da resposta (LLM-judge), robustez, perf e
similaridade semântica. Usada via `python -m einstein_test.eval`.
"""

from einstein_test.eval.dataset import EvalQuestion, load_dataset
from einstein_test.eval.generation import GenerationResult, run_generation
from einstein_test.eval.judge import FakeJudge, JudgeVerdict, LLMJudge
from einstein_test.eval.metrics import hit_rate_at_1, mrr_at_k, recall_at_k
from einstein_test.eval.report import render_report
from einstein_test.eval.runner import EvalReport, QuestionResult, run_eval

__all__ = [
    "EvalQuestion",
    "load_dataset",
    "GenerationResult",
    "run_generation",
    "FakeJudge",
    "LLMJudge",
    "JudgeVerdict",
    "recall_at_k",
    "mrr_at_k",
    "hit_rate_at_1",
    "render_report",
    "EvalReport",
    "QuestionResult",
    "run_eval",
]