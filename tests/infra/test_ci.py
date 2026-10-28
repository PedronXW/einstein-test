"""Testes TDD da feature F-026 (CI GitHub Actions).

Valida a presença e estrutura do `.github/workflows/ci.yml` (job test com uv +
pytest -m "not integration", alembic check e ruff), sem executar o Actions.
"""

import pathlib

import yaml


def test_ac001_ci_workflow_exists():
    p = pathlib.Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"
    assert p.exists(), "ci.yml existe"
    content = p.read_text()
    # YAML 1.1 (pyyaml) interpreta 'on:' como bool; checamos o texto bruto
    assert "on:" in content, "campo 'on' presente"
    assert "push:" in content, "dispara em push"
    assert "pull_request:" in content, "dispara em pull_request"
    data = yaml.safe_load(content)
    assert "jobs" in data and "test" in data["jobs"], "job test presente"


def test_ac002_integration_excluded():
    p = pathlib.Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"
    content = p.read_text()
    assert '"not integration"' in content or "'not integration'" in content, (
        "CI exclui -m integration"
    )


def test_ac003_alembic_and_ruff_in_ci():
    p = pathlib.Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"
    content = p.read_text()
    assert "alembic" in content, "CI roda alembic"
    assert "ruff" in content, "CI roda ruff"


def test_ac003_ci_uses_uv_and_python312():
    p = pathlib.Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"
    content = p.read_text()
    assert "uv sync" in content or "uv sync --dev" in content, "usa uv sync"
    assert "3.12" in content, "python 3.12"


def test_ac004_ci_present_and_referenced():
    p = pathlib.Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"
    assert p.is_file(), "arquivo regular"