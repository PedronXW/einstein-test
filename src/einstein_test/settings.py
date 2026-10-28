"""Configuração centralizada da aplicação (fails fast).

`Settings` é uma dataclass frozen com os valores de configuração (lidos de
env/.env), exposta como um lazy singleton via `get_settings()`. O
`validate_settings()` valida as obrigatórias no startup (`create_app`/CLI) —
falha rápido em vez de quebrar em runtime.
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

ALLOWED_SCHEMES = ("postgresql://", "sqlite://")

_OBRIGATORIAS = (
    ("JWT_SECRET", "jwt_secret", "secret de assinatura do JWT"),
    ("OPENAI_API_KEY", "openai_api_key", "chave da API OpenAI-compatível"),
    ("ALLOWED_MODELS", "allowed_models", "modelos de LLM permitidos"),
    ("DATABASE_URL", "database_url", "URL do banco de dados"),
)


class SettingsError(RuntimeError):
    """Lançada quando a configuração é inválida (fails fast no startup)."""


@dataclass(frozen=True)
class Settings:
    # banco / pool
    database_url: str = "postgresql://einstein:einstein@localhost:5432/einstein"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_timeout: float = 30.0
    # auth
    jwt_secret: str = ""
    access_token_expire_minutes: int = 60
    # openai / rag
    openai_api_key: str = ""
    openai_base_url: str = "https://spillway.ensinoeinstein.com/openai/v1"
    openai_chat_model: str = "azure/gpt-5-mini"
    allowed_models: list[str] = field(
        default_factory=lambda: ["azure/gpt-5-mini", "azure/gpt-6-luna"]
    )
    llm_max_retries: int = 2
    llm_retry_backoff: float = 1.0
    # logging
    log_level: str = "INFO"
    # rate limit
    rate_limit_login: int = 10
    rate_limit_chats: int = 30
    rate_limit_messages: int = 20
    rate_limit_files: int = 10
    rate_limit_users: int = 20
    rate_limit_global: int = 120
    # celery / tasks
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    vectorize_max_retries: int = 3
    vectorize_retry_backoff: int = 2


def _env(name: str, default: str = "") -> str:
    load_dotenv()
    return os.getenv(name) or default


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return list(default)
    return [m.strip() for m in raw.split(",") if m.strip()]


@lru_cache(maxsize=1)
def _build_settings() -> Settings:
    return Settings(
        database_url=_env("DATABASE_URL", "postgresql://einstein:einstein@localhost:5432/einstein"),
        database_pool_size=_env_int("DATABASE_POOL_SIZE", 10),
        database_max_overflow=_env_int("DATABASE_MAX_OVERFLOW", 20),
        database_pool_timeout=_env_float("DATABASE_POOL_TIMEOUT", 30.0),
        jwt_secret=_env("JWT_SECRET"),
        access_token_expire_minutes=_env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 60),
        openai_api_key=_env("OPENAI_API_KEY"),
        openai_base_url=_env("OPENAI_BASE_URL", "https://spillway.ensinoeinstein.com/openai/v1"),
        openai_chat_model=_env("OPENAI_CHAT_MODEL", "azure/gpt-5-mini"),
        allowed_models=_env_list("ALLOWED_MODELS", ["azure/gpt-5-mini", "azure/gpt-6-luna"]),
        llm_max_retries=_env_int("LLM_MAX_RETRIES", 2),
        llm_retry_backoff=_env_float("LLM_RETRY_BACKOFF", 1.0),
        log_level=_env("LOG_LEVEL", "INFO"),
        rate_limit_login=_env_int("RATE_LIMIT_LOGIN", 10),
        rate_limit_chats=_env_int("RATE_LIMIT_CHATS", 30),
        rate_limit_messages=_env_int("RATE_LIMIT_MESSAGES", 20),
        rate_limit_files=_env_int("RATE_LIMIT_FILES", 10),
        rate_limit_users=_env_int("RATE_LIMIT_USERS", 20),
        rate_limit_global=_env_int("RATE_LIMIT_GLOBAL", 120),
        celery_broker_url=_env("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        celery_result_backend=_env("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
        vectorize_max_retries=_env_int("VECTORIZE_MAX_RETRIES", 3),
        vectorize_retry_backoff=_env_int("VECTORIZE_RETRY_BACKOFF", 2),
    )


def get_settings() -> Settings:
    """Retorna o singleton de configuração (lazy, cacheado)."""
    return _build_settings()


settings = get_settings  # alias conveniente


def validate_settings(s: Settings | None = None) -> None:
    """Valida as configurações obrigatórias; levanta SettingsError se inválida.

    Chamado no `create_app`/CLI para falhar rápido em vez de quebrar em
    runtime com config ausente.
    """
    s = s or get_settings()
    problems: list[str] = []
    if not s.jwt_secret:
        problems.append("JWT_SECRET: obrigatório (gere com openssl rand -hex 32)")
    if not s.openai_api_key:
        problems.append("OPENAI_API_KEY: obrigatória")
    if not s.allowed_models:
        problems.append("ALLOWED_MODELS: ao menos um modelo")
    if not s.database_url.startswith(ALLOWED_SCHEMES):
        problems.append(f"DATABASE_URL: deve começar com {ALLOWED_SCHEMES}")
    if problems:
        raise SettingsError("configuração inválida:\n- " + "\n- ".join(problems))