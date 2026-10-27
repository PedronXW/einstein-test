"""Testes TDD da feature F-010 (AC-007: migration pgvector + file_chunks).

Valida que a migration Alembic cria a extensão vector, a tabela file_chunks
com embedding vector(1536) e as colunas novas em files (chunk_ids,
vector_reference).
"""

import os
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = "postgresql://einstein:einstein@localhost:5432/einstein"


@pytest.fixture
def alembic_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
    return env


def test_ac007_migration_creates_extension(alembic_env: dict[str, str]) -> None:
    proc = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        env=alembic_env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "CREATE  EXTENSION IF NOT EXISTS vector" in proc.stdout or (
        "CREATE EXTENSION IF NOT EXISTS vector" in proc.stdout.replace("  ", " ")
    ), "migration emite CREATE EXTENSION vector"


def test_ac007_migration_creates_file_chunks(alembic_env: dict[str, str]) -> None:
    proc = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        env=alembic_env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "CREATE TABLE file_chunks" in proc.stdout, (
        "migration emite CREATE TABLE file_chunks"
    )


def test_ac007_migration_vector_1536(alembic_env: dict[str, str]) -> None:
    proc = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        env=alembic_env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "vector(1536)" in proc.stdout.lower(), "coluna embedding é vector(1536)"


def test_ac007_migration_alters_files(alembic_env: dict[str, str]) -> None:
    proc = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        env=alembic_env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "chunk_ids" in proc.stdout, "migration adiciona chunk_ids em files"
    assert "vector_reference" in proc.stdout, "migration adiciona vector_reference em files"