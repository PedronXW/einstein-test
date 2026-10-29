"""Fixtures dos testes de integração (F-024).

Sobrescreve as fixtures autouse do `tests/conftest.py` para que o fluxo
end-to-end seja REAL:

- `_jwt_secret` → mantém `OPENAI_API_KEY` real do ambiente (o root mocka
  `sk-teste`, o que impediria embeddings/LLM reais);
- `_mock_enqueue` → vira no-op: o upload publica de verdade no Redis e o
  worker (processo externo) vetoriza em background;
- `_storage_fake` → vira no-op: o client configura MinIO/S3 real, onde o
  worker baixa o arquivo.

O `tests/conftest.py` raiz continua valendo para o resto da suíte
(unitários/API) que não precisa de provedor/worker reais.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch):
    """Config obrigatória para o fails-fast; preserva OPENAI_API_KEY real."""
    monkeypatch.setenv("JWT_SECRET", "segredo-dos-testes-int-0123456789abcdefghijklmnop")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    if not os.getenv("OPENAI_API_KEY"):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-teste")
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini,azure/gpt-6-luna")


@pytest.fixture(autouse=True)
def _mock_enqueue():
    """No-op: a integração NÃO mocka a fila (publica no Redis de verdade)."""
    yield


@pytest.fixture(autouse=True)
def _storage_fake():
    """No-op: a integração NÃO força storage in-memory (usa MinIO real)."""
    yield
