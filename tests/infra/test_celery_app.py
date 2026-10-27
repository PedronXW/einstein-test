"""Testes TDD da feature F-015 (AC-006: Celery app + Redis no compose)."""


def test_ac006_celery_app_loadable():
    from einstein_test.tasks import celery_app

    assert celery_app.main == "einstein_test.tasks"


def test_ac006_celery_app_broker_configured():
    from einstein_test.tasks import celery_app

    assert celery_app.conf.get("broker_url") or celery_app.conf.broker_url, (
        "broker configurado"
    )


def test_ac006_celery_task_registered():
    from einstein_test.tasks import celery_app, vectorize_file

    assert vectorize_file.name == "einstein_test.tasks.vectorize_file"
    assert vectorize_file.name in celery_app.tasks


def test_ac006_redis_in_compose():
    import pathlib

    compose = pathlib.Path(__file__).resolve().parents[2] / "docker-compose.yml"
    content = compose.read_text()
    assert "redis" in content, "serviço redis no docker-compose"
    assert "redis:7" in content or "redis" in content


def test_ac006_celery_redis_deps_in_pyproject():
    import pathlib

    pyproject = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"
    content = pyproject.read_text()
    assert "celery" in content and "redis" in content, "deps celery e redis"