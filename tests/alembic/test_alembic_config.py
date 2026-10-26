"""Testes TDD da feature F-002 (Alembic configurado, sem migrations).

Valida AC-003 (deps), AC-004 (alembic.ini/env.py/DATABASE_URL/target_metadata)
e AC-005 (Base declarativa + versions/ vazio).
"""

import os
import pathlib
import subprocess
import sys
import tomllib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "docker-compose.yml"


def read(path) -> str:
    with open(path) as f:
        return f.read()


class TestAlembicConfig(unittest.TestCase):
    def setUp(self) -> None:
        self.env = dict(os.environ)
        self.env.setdefault(
            "DATABASE_URL",
            "postgresql://einstein:einstein@localhost:5432/einstein",
        )

    def test_ac003_deps_in_pyproject(self) -> None:
        with open(ROOT / "pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
        deps = pyproject["project"]["dependencies"]
        for dep in ("fastapi", "uvicorn", "httpx", "sqlalchemy", "alembic", "psycopg"):
            self.assertTrue(
                any(d.startswith(dep) for d in deps),
                f"dependencia {dep} declarada em [project].dependencies",
            )

    def test_ac004_alembic_ini_exists(self) -> None:
        self.assertTrue((ROOT / "alembic.ini").exists(), "alembic.ini presente")

    def test_ac004_env_py_has_default_url(self) -> None:
        env_py = ROOT / "alembic" / "env.py"
        self.assertTrue(env_py.exists(), "alembic/env.py presente")
        content = read(env_py)
        self.assertIn("DATABASE_URL", content, "env.py usa DATABASE_URL")
        self.assertIn("postgresql://einstein:einstein@localhost:5432/einstein",
                      content, "default aponta para o postgres do compose")

    def test_ac004_env_py_target_metadata(self) -> None:
        content = read(ROOT / "alembic" / "env.py")
        self.assertIn("target_metadata", content, "target_metadata definido")
        self.assertIn("Base.metadata", content, "aponta para Base.metadata")

    def test_ac004_env_py_executa_offline(self) -> None:
        proc = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head", "--sql"],
            cwd=ROOT,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0,
                         "env.py carrega e roda em modo offline (sem banco)")

    def test_ac004_compose_has_postgres(self) -> None:
        content = read(COMPOSE)
        self.assertIn("postgres:16-alpine", content, "postgres no compose")

    def test_ac005_base_declarativa(self) -> None:
        sys.path.insert(0, str(ROOT))
        try:
            from app.db.base import Base  # noqa: F401
        finally:
            sys.path.pop(0)
        self.assertIsNotNone(Base.metadata, "Base.metadata disponível")
        self.assertTrue(len(Base.metadata.tables) == 0,
                        "nenhuma tabela registrada (consistent com versions/ vazio)")

    def test_ac005_no_migrations(self) -> None:
        versions = ROOT / "alembic" / "versions"
        self.assertTrue(versions.is_dir(), "alembic/versions/ existe")
        migrations = [
            p for p in versions.iterdir()
            if p.name != ".gitkeep" and p.suffix == ".py"
        ]
        self.assertEqual(migrations, [], "nenhuma migration gerada")


if __name__ == "__main__":
    unittest.main()