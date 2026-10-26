"""Testes TDD da feature F-002 (Alembic configurado, sem migrations).

Valida AC-003 (deps), AC-004 (alembic.ini/env.py/DATABASE_URL/target_metadata)
e AC-005 (Base declarativa + versions/ vazio).
"""

import os
import pathlib
import subprocess
import tomllib

import pytest

from app.db.base import Base

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
    assert len(Base.metadata.tables) == 0, (
        "consistente com versions/ vazio"
    )


def test_ac005_no_migrations() -> None:
    versions = ROOT / "alembic" / "versions"
    assert versions.is_dir(), "alembic/versions/ existe"
    migrations = [
        p for p in versions.iterdir()
        if p.name != ".gitkeep" and p.suffix == ".py"
    ]
    assert migrations == [], "nenhuma migration gerada"