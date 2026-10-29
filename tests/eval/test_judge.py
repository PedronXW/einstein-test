"""Testes TDD da F-038 — AC-002: Judge (Fake determinístico + LLMJudge)."""

import json

from einstein_test.eval.judge import FakeJudge, LLMJudge, JudgeVerdict
from einstein_test.services.rag.llm import FakeChatLLM


def _verdict_is_valid(v: JudgeVerdict):
    assert 1 <= v.correctness <= 5
    assert 1 <= v.faithfulness <= 5
    assert 1 <= v.coverage <= 5


def test_ac002_fake_judge_high_score_on_gold_overlap():
    judge = FakeJudge()
    v = judge.judge(
        question="qual a data de lançamento?",
        gold_answer="O produto foi lançado em 2021.",
        answer="Lançado em 2021.",
        context=["O produto foi lançado em 2021."],
    )
    _verdict_is_valid(v)
    assert v.correctness >= 4, "resposta cobre o gold -> correção alta"


def test_ac002_fake_judge_low_score_on_missing_gold():
    judge = FakeJudge()
    v = judge.judge(
        question="qual a data de lançamento?",
        gold_answer="o produto foi lançado em 2021",
        answer="resposta totalmente desconexa sobre outro assunto",
        context=["O produto foi lançado em 2021."],
    )
    _verdict_is_valid(v)
    assert v.correctness <= 2, "resposta não cobre o gold -> correção baixa"


def test_ac002_llm_judge_parses_verdict_from_tokens():
    """LLMJudge usa um ChatLLM que devolve JSON no stream — parse determinístico."""
    fake = FakeChatLLM(tokens=[json.dumps({
        "correctness": 4, "faithfulness": 5, "coverage": 3,
        "rationale": "resposta correta e ancorada",
    })])
    judge = LLMJudge(llm=fake)
    v = judge.judge(
        question="q", gold_answer="g", answer="a", context=["c"],
    )
    assert v.correctness == 4
    assert v.faithfulness == 5
    assert v.coverage == 3
    assert "ancorada" in v.rationale


def test_ac002_llm_judge_parses_json_embedded_in_text():
    fake = FakeChatLLM(tokens=['Aqui: {"correctness": 4, "faithfulness": 5, "coverage": 3} fim'])
    v = LLMJudge(llm=fake).judge(question="q", gold_answer="g", answer="a", context=["c"])
    assert v.correctness == 4 and v.faithfulness == 5 and v.coverage == 3


def test_ac002_llm_judge_fallback_clamps_garbage():
    fake = FakeChatLLM(tokens=["texto sem json nenhum"])
    v = LLMJudge(llm=fake).judge(question="q", gold_answer="g", answer="a", context=["c"])
    assert 1.0 <= v.correctness <= 5.0
    assert 1.0 <= v.faithfulness <= 5.0
    assert 1.0 <= v.coverage <= 5.0


def test_ac002_fake_judge_floor_with_empty_answer():
    v = FakeJudge().judge(answer="", gold_answer="x", context=["c"])
    assert v.correctness == 1.0
    assert v.faithfulness == 1.0
    assert v.coverage == 1.0