"""Testes TDD da feature F-031 (AC-006: engine factory em db/, task usa db/).

Valida que `create_engine_from_config` mora em `einstein_test.db.engine` e que a
task de vetorização importa de `db`, nunca de `api`.
"""

import pytest

from einstein_test.db.engine import create_engine_from_config


def test_ac006_engine_factory_lives_in_db():
    engine = create_engine_from_config("sqlite:///:memory:")
    assert engine is not None
    engine.dispose()


def test_ac006_task_imports_from_db_not_api():
    import einstein_test.tasks as tasks

    src = pytest.importorskip("inspect").getsource(tasks)
    assert "einstein_test.api.dependencies" not in src, (
        "task não deve importar engine de api.dependencies"
    )
    assert "einstein_test.db.engine" in src, "task importa engine de db.engine"


def test_ac006_api_dependencies_reuses_db():
    import einstein_test.api.dependencies as deps

    assert deps.create_engine_from_config is create_engine_from_config
