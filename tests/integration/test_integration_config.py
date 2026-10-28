"""Testes TDD da feature F-024 (marker integration + addopts).

Valida que o marker `integration` está registrado, o CI padrão exclui a
integração (`-m "not integration"`), e que o arquivo de integração skipa
graciosamente sem chave/infra.
"""

import pathlib

import pytest


def test_ac001_integration_marker_registered():
    pyproject = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"
    content = pyproject.read_text()
    assert 'markers' in content
    assert 'integration' in content, "marker integration registrado no pyproject"


def test_ac001_default_ci_excludes_integration():
    pyproject = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"
    content = pyproject.read_text()
    # addopts contém -m "not integration" (no TOML, com escape \")
    assert "not integration" in content, "addopts exclui integração"
    assert "addopts" in content, "addopts definido"
    # a exclusão é um -m "not ..." (exclui, não seleciona)
    assert "not integration" in content.split("addopts")[1], (
        "addopts usa -m not integration (exclusão)"
    )


def test_ac002_integration_file_skips_without_env():
    # o teste de integração deve skipar (não falhar) sem OPENAI_API_KEY/RUN_INTEGRATION
    import os

    if os.getenv("OPENAI_API_KEY") and os.getenv("RUN_INTEGRATION") == "1":
        pytest.skip("integracao configurada — skip no teste de config")
    # sem env: o import do módulo de integração não deve estourar
    import importlib.util

    p = pathlib.Path(__file__).resolve().parent / "test_rag_end_to_end.py"
    spec = importlib.util.spec_from_file_location("test_rag_end_to_end", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # deve funcionar (fixture skipa)
    assert hasattr(mod, "test_rag_end_to_end")


def test_ac004_integration_marker_descriptor():
    # o arquivo de integração declara o marker no teste
    p = pathlib.Path(__file__).resolve().parent / "test_rag_end_to_end.py"
    content = p.read_text()
    assert "integration" in content, "teste usa @pytest.mark.integration"