"""Testes TDD da feature F-002/F-004 (Alembic configurado + models).

Valida AC-003 (deps), AC-004 (alembic.ini/env.py/DATABASE_URL/target_metadata)
e AC-005 (Base registra as models Chat/File/Message da F-004).
"""

import os
import pathlib
import subprocess
import tomllib

import pytest

from einstein_test.db.base import Base
from einstein_test.models import Chat, File, Message  # noqa: F401  (registra as tabelas)

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "docker-compose.yml"

DEFAULT_DATABASE_URL = "postgresql://einstein:einstein@localhost:5432/einstein"


@pytest.fixture
def alembic_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
    return env


def read(path: pathlib.Path) -> str:
    return path.read_text()


def test_ac003_deps_in_pyproject() -> None:
    with open(ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    deps = pyproject["project"]["dependencies"]
    for dep in ("fastapi", "uvicorn", "httpx", "sqlalchemy", "alembic", "psycopg"):
        assert any(d.startswith(dep) for d in deps), (
            f"dependencia {dep} declarada em [project].dependencies"
        )


def test_ac004_alembic_ini_exists() -> None:
    assert (ROOT / "alembic.ini").exists(), "alembic.ini presente"


def test_ac004_env_py_has_default_url() -> None:
    env_py = ROOT / "alembic" / "env.py"
    assert env_py.exists(), "alembic/env.py presente"
    content = read(env_py)
    assert "DATABASE_URL" in content, "env.py usa DATABASE_URL"
    assert DEFAULT_DATABASE_URL in content, "default aponta para o postgres do compose"


def test_ac004_env_py_target_metadata() -> None:
    content = read(ROOT / "alembic" / "env.py")
    assert "target_metadata" in content, "target_metadata definido"
    assert "Base.metadata" in content, "aponta para Base.metadata"


def test_ac004_env_py_executa_offline(alembic_env: dict[str, str]) -> None:
    proc = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        env=alembic_env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_ac004_compose_has_postgres() -> None:
    content = read(COMPOSE)
    assert "postgres:16-alpine" in content, "postgres no compose"


def test_ac005_base_declarativa() -> None:
    assert Base.metadata is not None, "Base.metadata disponivel"
    expected = {"chats", "files", "messages"}
    assert expected <= set(Base.metadata.tables), (
        "Base registra as models da F-004 (chats, files, messages)"
    )


def test_ac006_migration_crea_tables(alembic_env: dict[str, str]) -> None:
    versions = ROOT / "alembic" / "versions"
    migrations = [
        p for p in versions.iterdir()
        if p.suffix == ".py" and p.name != "__init__.py"
    ]
    assert migrations, "ao menos uma migration gerada"
    proc = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        env=alembic_env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for table in ("chats", "files", "messages"):
        assert f"CREATE TABLE {table}" in proc.stdout, (
            f"migration offline emite CREATE TABLE {table}"
        )