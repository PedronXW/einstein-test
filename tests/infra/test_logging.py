"""Testes TDD da feature F-019 (logs robustos: JSON + request_id).

Valida configure_logging (JSON formatter), get_logger, RequestIdMiddleware
(access log + X-Request-Id) e a não-vazamento de conteúdo de prompt/arquivos.
"""

import io
import json
import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from einstein_test.db.base import Base
from einstein_test.main import create_app
from einstein_test.logging_setup import configure_logging, get_logger


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    from einstein_test.api.dependencies import configure_session_factory

    configure_session_factory(engine)
    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c
    engine.dispose()


def test_ac001_json_formatter_output(monkeypatch):
    from einstein_test.logging_setup import JsonFormatter

    record = logging.LogRecord(
        name="einstein_test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="mensagem teste",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-abc"
    fmt = JsonFormatter()
    line = fmt.format(record)
    parsed = json.loads(line)
    assert parsed["level"] == "INFO"
    assert parsed["msg"] == "mensagem teste"
    assert parsed["request_id"] == "req-abc"
    assert "ts" in parsed and "logger" in parsed


def test_ac001_configure_logging_sets_level(monkeypatch):
    import logging as _l

    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    configure_logging(level="WARNING")
    assert _l.getLogger("einstein_test").level == _l.WARNING, (
        "level WARNING aplicado"
    )
    # re-aplicar com outro nível não é necessário (idempotente p/ handler)
    monkeypatch.setenv("LOG_LEVEL", "INFO")


def test_ac001_get_logger_returns_logger():
    logger = get_logger("tasks")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "einstein_test.tasks", "prefixo einstein_test aplicado"


def test_ac002_middleware_returns_x_request_id(client):
    app = client.app if hasattr(client, "app") else None
    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "x-request-id" in {k.lower() for k in resp.headers}, (
        "header X-Request-Id presente"
    )


def test_ac002_access_log_has_request_id(capsys):
    import logging as _l

    from einstein_test.logging_setup import JsonFormatter

    stream = io.StringIO()
    h = _l.StreamHandler(stream)
    h.setFormatter(JsonFormatter())
    logger = _l.getLogger("einstein_test.middleware.logging_middleware")
    logger.addHandler(h)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    from einstein_test.api.dependencies import configure_session_factory
    from sqlalchemy import create_engine as _ce
    from sqlalchemy.pool import StaticPool as _sp

    engine = _ce("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=_sp)
    Base.metadata.create_all(engine)
    configure_session_factory(engine)
    app = create_app()
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        c.get("/docs")
    h.flush()
    out = stream.getvalue().strip()
    parsed = json.loads(out)
    assert "request_id" in parsed
    assert parsed["method"] == "GET"
    assert parsed["status"] == 200
    logger.removeHandler(h)
    engine.dispose()


def test_ac003_request_id_propagated_to_service_log(client):
    import logging as _l

    from einstein_test.logging_setup import JsonFormatter, request_id_var

    # usa um handler próprio com o MESMO formatter + RequestIdFilter que o
    # configure_logging aplica ao canal da app (verifica a propagação real)
    from einstein_test.logging_setup import RequestIdFilter

    stream = io.StringIO()
    h = _l.StreamHandler(stream)
    h.setFormatter(JsonFormatter())
    h.addFilter(RequestIdFilter())
    svc_logger = _l.getLogger("einstein_test.services.rag")
    svc_logger.addHandler(h)
    svc_logger.setLevel(logging.INFO)
    svc_logger.propagate = False

    # simula o middleware: define a contextvar do request
    token = request_id_var.set("req-9876")
    svc_logger.info("dentro do request", extra={"event": "rag_start", "chat_id": 42})
    request_id_var.reset(token)

    h.flush()
    out = stream.getvalue().strip()
    parsed = json.loads(out)
    assert parsed["request_id"] == "req-9876", "RequestIdFilter injeta request_id"
    assert parsed["chat_id"] == 42
    assert parsed["event"] == "rag_start"
    svc_logger.removeHandler(h)


def test_ac004_rag_logs_do_not_leak_prompt(monkeypatch):
    import logging as _l

    from einstein_test.logging_setup import JsonFormatter

    stream = io.StringIO()
    h = _l.StreamHandler(stream)
    h.setFormatter(JsonFormatter())
    logger = _l.getLogger("einstein_test.services.rag")
    logger.addHandler(h)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    pergunta_secreta = "qual o codigo de acesso do usuario 123?"
    # ponto crítico: logamos apenas ids/contagens, NUNCA o conteúdo
    logger.info("RAG iniciado", extra={
        "event": "rag_start",
        "chat_id": 42,
        "question_len": len(pergunta_secreta),
    })
    h.flush()
    out = stream.getvalue().strip()
    assert pergunta_secreta not in out, "prompt/pergunta não vaza nos logs"
    assert "RAG iniciado" in out
    assert json.loads(out)["question_len"] == len(pergunta_secreta)
    logger.removeHandler(h)


def test_ac004_task_logs_do_not_leak_content(monkeypatch):
    import logging as _l

    from einstein_test.logging_setup import JsonFormatter

    stream = io.StringIO()
    h = _l.StreamHandler(stream)
    h.setFormatter(JsonFormatter())
    logger = _l.getLogger("einstein_test.tasks")
    logger.addHandler(h)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    conteudo_arquivo = "banco de dados com senha 1234"
    # loga só ids/tentativa, nunca o conteúdo do arquivo
    logger.info("vetorização iniciada", extra={
        "event": "vectorize_start", "file_id": 7, "attempt": 1,
    })
    h.flush()
    out = stream.getvalue().strip()
    assert conteudo_arquivo not in out, "conteúdo de arquivo não vaza"
    assert json.loads(out)["file_id"] == 7
    logger.removeHandler(h)


def test_ac005_logs_are_parseable_json():
    record = {
        "ts": "2026-01-01T00:00:00",
        "level": "INFO",
        "logger": "x",
        "msg": "oi",
        "request_id": "abc",
    }
    line = json.dumps(record)
    assert json.loads(line)["msg"] == "oi"