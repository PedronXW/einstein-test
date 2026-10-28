"""Testes TDD da feature F-025 (settings central + fails fast).

Valida: Settings dataclass lazy, validate_settings (obrigatórios + formato),
e a leitura central sem quebrar o comportamento.
"""

import pytest

from einstein_test.settings import Settings, SettingsError, get_settings, validate_settings


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    # isola os testes de env
    import einstein_test.settings as s

    s._build_settings.cache_clear()
    for k in ("JWT_SECRET", "OPENAI_API_KEY", "ALLOWED_MODELS", "DATABASE_URL"):
        monkeypatch.delenv(k, raising=False)
    yield
    s._build_settings.cache_clear()


def test_ac001_settings_dataclass_frozen():
    s = Settings(
        database_url="postgresql://u:p@localhost/db",
        jwt_secret="s" * 32,
        openai_api_key="sk-test",
        allowed_models=["azure/gpt-5-mini", "azure/gpt-6-luna"],
    )
    with pytest.raises(AttributeError):
        s.jwt_secret = "outro"  # frozen


def test_ac001_get_settings_lazy_singleton(monkeypatch):
    import einstein_test.settings as s

    monkeypatch.setenv("JWT_SECRET", "s" * 32)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    s._settings = None
    a = get_settings()
    b = get_settings()
    assert a is b, "singleton (mesma instância)"
    assert a.jwt_secret == "s" * 32
    assert a.allowed_models == ["azure/gpt-5-mini"]


def test_ac002_validate_accepts_valid():
    s = Settings(
        database_url="postgresql://u:p@localhost/db",
        jwt_secret="s" * 32,
        openai_api_key="sk-test",
        allowed_models=["azure/gpt-5-mini"],
    )
    validate_settings(s)  # não levanta


def test_ac002_validate_rejects_empty_jwt():
    s = Settings(
        database_url="postgresql://u:p@localhost/db",
        jwt_secret="",
        openai_api_key="sk-test",
        allowed_models=["azure/gpt-5-mini"],
    )
    with pytest.raises(SettingsError) as e:
        validate_settings(s)
    assert "JWT_SECRET" in str(e.value)


def test_ac002_validate_rejects_empty_api_key():
    s = Settings(
        database_url="postgresql://u:p@localhost/db",
        jwt_secret="s" * 32,
        openai_api_key="",
        allowed_models=["azure/gpt-5-mini"],
    )
    with pytest.raises(SettingsError) as e:
        validate_settings(s)
    assert "OPENAI_API_KEY" in str(e.value)


def test_ac002_validate_rejects_empty_allowed_models():
    s = Settings(
        database_url="postgresql://u:p@localhost/db",
        jwt_secret="s" * 32,
        openai_api_key="sk-test",
        allowed_models=[],
    )
    with pytest.raises(SettingsError) as e:
        validate_settings(s)
    assert "ALLOWED_MODELS" in str(e.value)


def test_ac002_validate_rejects_bad_database_url():
    s = Settings(
        database_url="mysql://u:p@localhost/db",
        jwt_secret="s" * 32,
        openai_api_key="sk-test",
        allowed_models=["azure/gpt-5-mini"],
    )
    with pytest.raises(SettingsError) as e:
        validate_settings(s)
    assert "DATABASE_URL" in str(e.value)


def test_ac002_validate_accepts_sqlite():
    s = Settings(
        database_url="sqlite:///:memory:",
        jwt_secret="s" * 32,
        openai_api_key="sk-test",
        allowed_models=["azure/gpt-5-mini"],
    )
    validate_settings(s)  # sqlite é aceito (testes/dev)


def test_ac004_create_app_calls_validate_settings(monkeypatch):
    # o create_app chama validate_settings (fails fast) — provamos via mock
    import einstein_test.main as main

    called = {"n": 0}

    def _fake_validate(cfg=None):
        called["n"] += 1

    monkeypatch.setattr(main, "validate_settings", _fake_validate)
    from einstein_test.main import create_app

    # precisa do env válido p/ não estourar no restante do create_app
    monkeypatch.setenv("JWT_SECRET", "s" * 32)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ALLOWED_MODELS", "azure/gpt-5-mini")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    app = create_app()
    assert called["n"] == 1, "create_app chamou validate_settings"
    assert app is not None