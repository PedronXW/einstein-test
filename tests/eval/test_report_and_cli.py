"""Testes TDD da F-038 — AC-004/AC-005: relatório e CLI (smoke determinístico)."""

import json

from einstein_test.eval.cli import main as cli_main
from einstein_test.eval.dataset import EvalQuestion
from einstein_test.eval.judge import JudgeVerdict
from einstein_test.eval.report import render_report
from einstein_test.eval.runner import EvalReport, QuestionResult, RetrievalMetrics


def _sample_question():
    return EvalQuestion(
        id="q1",
        question="Quando foi lançado?",
        expected_files=("produto.md",),
        gold_answer="em 2021",
    )


def _sample_report():
    q = _sample_question()
    result = QuestionResult(
        question=q,
        metrics=RetrievalMetrics(recall_5=1.0, recall_12=1.0, mrr_5=1.0, hit_1=1.0),
        verdict=JudgeVerdict(correctness=5.0, faithfulness=5.0, coverage=5.0),
        similarity=0.99,
        answer="em 2021",
        ttft=0.05,
        latency=0.10,
        robustness_ok=True,
    )
    return EvalReport(results=[result])


def test_ac004_report_markdown_renders():
    md = render_report(_sample_report(), "md")
    assert "q1" in md and "recall@5" in md and "correctness" in md


def test_ac004_report_html_renders():
    html = render_report(_sample_report(), "html")
    assert "<html" in html.lower() or "<table" in html.lower()
    assert "q1" in html


def test_ac004_report_html_escapes_question():
    report = _sample_report()
    report.results[0].question = EvalQuestion(
        id="q1", question="<b>x</b>", expected_files=("produto.md",), gold_answer="g"
    )
    html = render_report(report, "html")
    assert "&lt;b&gt;x&lt;/b&gt;" in html


def test_ac005_cli_smoke_fake_backend(tmp_path):
    dataset = tmp_path / "dev.jsonl"
    dataset.write_text(json.dumps({
        "id": "q1", "question": "Quando foi lançado?",
        "expected_files": ["produto.md"], "gold_answer": "em 2021",
    }) + "\n")
    out = tmp_path / "out.json"
    exit_code = cli_main([
        "--backend", "fake",
        "--judge", "fake",
        "--limit", "1",
        "--dataset", str(dataset),
        "--format", "json",
        "--out", str(out),
    ])
    assert exit_code == 0
    data = json.loads(out.read_text())
    assert len(data["results"]) == 1
    r = data["results"][0]
    assert r["question"]["id"] == "q1"
    assert r["metrics"]["recall_5"] == 1.0
    assert r["verdict"]["correctness"] >= 4


def test_ac004_cli_without_out_prints_content(tmp_path, capsys):
    dataset = tmp_path / "dev.jsonl"
    dataset.write_text(json.dumps({
        "id": "q1", "question": "Quando foi lançado?",
        "expected_files": ["produto.md"], "gold_answer": "em 2021",
    }) + "\n")
    exit_code = cli_main([
        "--backend", "fake", "--limit", "1", "--dataset", str(dataset), "--format", "json",
    ])
    assert exit_code == 0
    assert '"results"' in capsys.readouterr().out


def test_ac005_cli_empty_dataset_exits_1(tmp_path, capsys):
    dataset = tmp_path / "dev.jsonl"
    dataset.write_text("")
    exit_code = cli_main(["--backend", "fake", "--dataset", str(dataset)])
    assert exit_code == 1
    assert "dataset vazio" in capsys.readouterr().out


def test_ac005_cli_missing_corpus_exits_1(tmp_path, capsys):
    dataset = tmp_path / "dev.jsonl"
    dataset.write_text(json.dumps({
        "id": "q1", "question": "pergunta",
        "expected_files": ["produto.md"], "gold_answer": "g",
    }) + "\n")
    exit_code = cli_main([
        "--backend", "fake", "--dataset", str(dataset), "--corpus", str(tmp_path / "nope"),
    ])
    assert exit_code == 1
    assert "corpus não encontrado" in capsys.readouterr().out