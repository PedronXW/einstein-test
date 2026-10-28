"""Testes TDD da feature F-032 (AC-001/AC-002: follow-ups de layering).

AC-001: MAX_HISTORY vive em MessageService (fonte única), não no controller.
AC-002: JWT helpers moram em `security`; middleware importa de `security`,
nunca de `api`; `api/auth.py` reutiliza de `security`.
"""

import inspect


def test_ac001_max_history_lives_in_message_service():
    from einstein_test.services.message import MAX_HISTORY

    assert MAX_HISTORY == 10


def test_ac001_controller_imports_max_history_from_service():
    import einstein_test.api.messages as messages_api

    src = inspect.getsource(messages_api)
    assert "from einstein_test.services.message import" in src, (
        "controller importa MAX_HISTORY de services.message"
    )
    assert "MAX_HISTORY =" not in src, "controller não define MAX_HISTORY"


def test_ac002_security_has_jwt_helpers():
    import einstein_test.security as security

    assert hasattr(security, "create_access_token")
    assert hasattr(security, "decode_token")


def test_ac002_auth_reuses_jwt_helpers_from_security():
    import einstein_test.security as security
    from einstein_test.api import auth as auth_api

    src = inspect.getsource(auth_api)
    assert "from einstein_test.security import" in src, (
        "api/auth reutiliza helpers JWT de security"
    )
    assert auth_api.create_access_token is security.create_access_token
    assert auth_api.decode_token is security.decode_token


def test_ac002_middleware_imports_from_security_not_api():
    import einstein_test.middleware.logging_middleware as lm
    import einstein_test.middleware.rate_limit as rl

    for name, mod in (("logging_middleware", lm), ("rate_limit", rl)):
        src = inspect.getsource(mod)
        assert "einstein_test.security" in src, f"{name}: importa de security"
        assert "einstein_test.api" not in src, f"{name}: não importa da camada api"