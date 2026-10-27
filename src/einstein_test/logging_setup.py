"""Configuração de logging (JSON estruturado + request_id).

- `request_id_var`/`current_request_id()`: contexto do request atual.
- `RequestIdFilter`: injeta o `request_id` no LogRecord (anexado ao handler,
  propaga a todos os registros da hierarquia da app).
- `configure_logging()`: aplica JSON formatter + o filtro ao handler da app,
  STDOUT, nível via `LOG_LEVEL` (default INFO).
- `get_logger(name)`: retorna `einstein_test.<name>` (herda o formatter).
- `JsonFormatter`: serializa campos conhecidos como uma linha JSON.
"""

import json
import logging
import os
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    """Retorna o request_id do request corrente (ou None fora de request)."""
    return request_id_var.get()


class RequestIdFilter(logging.Filter):
    """Injeta `request_id` atual nos LogRecords (para o formatter JSON)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = current_request_id()
        return True


_configured = False

# Campos conhecidos serializados no JSON (whitelist — nunca logar conteúdo
# livre/segredos via extra).
_KNOWN_FIELDS = (
    "request_id", "event", "chat_id", "file_id", "message_id", "attempt",
    "status", "latency_ms", "user_id", "method", "path", "n_tokens",
    "question_len", "retry_in", "error", "endpoint", "ip",
)


class JsonFormatter(logging.Formatter):
    """Formatter que emite cada registro como uma linha JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in _KNOWN_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str | None = None) -> None:
    """Configura o logging da aplicação (JSON no STDOUT). Idempotente."""
    global _configured
    level = level or os.getenv("LOG_LEVEL", "INFO")
    root = logging.getLogger("einstein_test")
    root.setLevel(level.upper())
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger da app (namespace `einstein_test.*`)."""
    configure_logging()
    return logging.getLogger(f"einstein_test.{name}")