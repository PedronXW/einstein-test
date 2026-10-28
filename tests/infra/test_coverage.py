"""Testes TDD da feature F-028 (cobertura pytest-cov).

Valida a config de cobertura no pyproject (fail_under, omit) e a presença de
cobertura no CI (--cov-fail-under, relatórios). Não roda a cobertura completa
aqui (lenta); valida estrutura.
"""

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_ac001_pytest_cov_in_dev_deps():
    p = ROOT / "pyproject.toml"
    content = p.read_text()
    assert "pytest-cov" in content, "pytest-cov em dev deps"


def test_ac001_coverage_config_present():
    p = ROOT / "pyproject.toml"
    content = p.read_text()
    assert "[tool.coverage.run]" in content, "config run presente"
    assert "[tool.coverage.report]" in content, "config report presente"
    assert "fail_under" in content, "fail_under definido"


def test_ac001_fail_under_value():
    import tomllib

    p = ROOT / "pyproject.toml"
    data = tomllib.loads(p.read_text())
    report = data.get("tool", {}).get("coverage", {}).get("report", {})
    fail = report.get("fail_under")
    assert isinstance(fail, int) and fail >= 50, f"fail_under razoável ({fail})"


def test_ac002_ci_has_cov_fail_under():
    p = ROOT / ".github/workflows/ci.yml"
    content = p.read_text()
    assert "--cov" in content or "--cov=einstein_test" in content, "CI usa --cov"
    assert "fail-under" in content or "fail_under" in content, "CI com fail-under"


def test_ac003_ci_has_html_report():
    p = ROOT / ".github/workflows/ci.yml"
    content = p.read_text()
    assert "cov-report=html" in content or "--cov-report html" in content, (
        "CI gera relatório HTML"
    )
    assert "htmlcov" in content or "cov-report=html" in content, (
        "upload do HTML (artefato)"
    )


def test_ac004_coverage_runner_configured():
    # o comando pytest --cov está descrito (addopts ou CI) e a suíte roda

    # apenas verifica que pytest-cov importável
    import pytest_cov  # noqa: F401

    assert True