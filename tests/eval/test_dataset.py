"""Testes TDD da F-038 — AC-004/AC-005: dataset (JSONL + corpus)."""

import json

import pytest

from einstein_test.eval.dataset import EvalQuestion, load_corpus_file, load_dataset


def test_dataset_loads_jsonl(tmp_path):
    q = tmp_path / "dev.jsonl"
    q.write_text(json.dumps({
        "id": "q1",
        "question": "Quando foi lançado?",
        "expected_files": ["produto.md"],
        "gold_answer": "em 2021",
        "domain": "synthetic",
    }) + "\n" + json.dumps({
        "id": "q2",
        "question": "O que faz?",
        "expected_files": ["produto.md", "time.md"],
        "gold_answer": "resposta",
        "domain": "natural",
        "edge": "no_context",
    }) + "\n")
    questions = load_dataset(q)
    assert len(questions) == 2
    assert questions[0] == EvalQuestion(
        id="q1", question="Quando foi lançado?",
        expected_files=("produto.md",), gold_answer="em 2021", domain="synthetic",
    )
    assert questions[1].expected_files == ("produto.md", "time.md")
    assert questions[1].edge == "no_context"


def test_dataset_skips_blank_lines(tmp_path):
    q = tmp_path / "dev.jsonl"
    q.write_text("\n\n{\"id\": \"q1\", \"question\": \"pergunta\", "
                 "\"expected_files\": [], \"gold_answer\": \"g\"}\n")
    assert len(load_dataset(q)) == 1


def test_corpus_loads_and_blocks_traversal(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.md").write_text("conteudo")
    assert load_corpus_file(corpus, "a.md") == b"conteudo"
    with pytest.raises(ValueError):
        load_corpus_file(corpus, "../.env")