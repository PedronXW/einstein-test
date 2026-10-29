"""Juiz de resposta: Fake determinístico e LLM-judge (rubric 1–5)."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Protocol

from einstein_test.services.rag.llm import ChatLLM, ChatOpenAIAdapter

EVAL_JUDGE_MODEL = os.getenv("EVAL_JUDGE_MODEL", "azure/gpt-6-luna")

_JUDGE_PROMPT = (
    "Você avalia respostas de um sistema RAG. Dê notas de 1 a 5 em:\n"
    "- correctness: correta em relação à resposta de referência (gold)?\n"
    "- faithfulness: ancorada no contexto fornecido, sem alucinação?\n"
    "- coverage: cobre a pergunta?\n"
    "Responda APENAS em JSON: "
    '{{"correctness": n, "faithfulness": n, "coverage": n, "rationale": "..."}}\n'
    "Pergunta: {question}\n"
    "Resposta de referência (gold): {gold}\n"
    "<contexto>\n{context}\n</contexto>\n"
    "Resposta do assistente: {answer}\n"
    "JSON:"
)


@dataclass
class JudgeVerdict:
    correctness: float
    faithfulness: float
    coverage: float
    rationale: str = ""


class Judge(Protocol):
    def judge(
        self,
        *,
        question: str,
        gold_answer: str,
        answer: str,
        context: list[str],
    ) -> JudgeVerdict: ...


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9áéíóúâêôãõçà ]", " ", text.lower())


def _tokens(text: str) -> set[str]:
    return {t for t in _norm(text).split() if t}


def _overlap(haystack: set[str], tokens: set[str]) -> float:
    if not tokens:
        return 0.0
    return len(haystack & tokens) / len(tokens)


def _clamp(score: float) -> float:
    """Mantém o escore dentro do rubric 1–5."""
    return round(min(max(score, 1.0), 5.0), 2)


class FakeJudge:
    """Determinístico: notas derivadas de sobreposição de tokens (sem chave)."""

    def judge(
        self,
        *,
        question: str = "",
        gold_answer: str = "",
        answer: str = "",
        context: list[str] | None = None,
    ) -> JudgeVerdict:
        context = context or []
        gold_toks = _tokens(gold_answer)
        ans_toks = _tokens(answer)
        ctx_toks = _tokens(" ".join(context))
        correctness = _clamp(1.0 + 4.0 * _overlap(gold_toks, ans_toks))
        coverage = _clamp(1.0 + 4.0 * _overlap(ans_toks, gold_toks))
        faithfulness = _clamp(1.0 + 4.0 * _overlap(ctx_toks | gold_toks, ans_toks))
        return JudgeVerdict(
            correctness=correctness,
            faithfulness=faithfulness,
            coverage=coverage,
            rationale="fake",
        )


def _parse_judge_json(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        raw = raw[start : end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        nums = re.findall(
            r'"\s*(correctness|faithfulness|coverage)\s*"\s*:\s*(\d+(?:\.\d+)?)', raw
        )
        return {k: float(v) for k, v in nums}


class LLMJudge:
    """Juiz via LLM (ChatOpenAIAdapter) com rubric; parse do JSON retornado."""

    def __init__(self, llm: ChatLLM | None = None, model: str | None = None) -> None:
        self._llm: ChatLLM = llm or ChatOpenAIAdapter(model=model or EVAL_JUDGE_MODEL)

    def judge(
        self,
        *,
        question: str,
        gold_answer: str,
        answer: str,
        context: list[str],
    ) -> JudgeVerdict:
        prompt = _JUDGE_PROMPT.format(
            question=question,
            gold=gold_answer or "(vazio)",
            context="\n".join(context) if context else "(vazio)",
            answer=answer,
        )
        raw = "".join(self._llm.stream(prompt))
        data = _parse_judge_json(raw)
        return JudgeVerdict(
            correctness=_clamp(float(data.get("correctness", 0) or 0)),
            faithfulness=_clamp(float(data.get("faithfulness", 0) or 0)),
            coverage=_clamp(float(data.get("coverage", 0) or 0)),
            rationale=str(data.get("rationale", "") or ""),
        )