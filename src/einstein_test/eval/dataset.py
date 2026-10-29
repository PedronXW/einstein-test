"""Dataset gold de avaliação: perguntas + arquivos esperados + gold answer."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvalQuestion:
    id: str
    question: str
    expected_files: tuple[str, ...] = ()
    gold_answer: str = ""
    domain: str = "synthetic"
    edge: str = ""


def load_dataset(path: Path) -> list[EvalQuestion]:
    """Carrega o dataset JSONL (uma pergunta por linha)."""
    questions: list[EvalQuestion] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            questions.append(
                EvalQuestion(
                    id=item["id"],
                    question=item["question"],
                    expected_files=tuple(item.get("expected_files", [])),
                    gold_answer=item.get("gold_answer", ""),
                    domain=item.get("domain", "synthetic"),
                    edge=item.get("edge", ""),
                )
            )
    return questions


def load_corpus_file(corpus_dir: Path, name: str) -> bytes:
    """Lê um documento do corpus pelo nome relativo (sem path traversal)."""
    safe = (corpus_dir / name).resolve()
    if not safe.is_relative_to(corpus_dir.resolve()):
        raise ValueError(f"nome de corpus inválido: {name!r}")
    return safe.read_bytes()