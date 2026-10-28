# Imagem da aplicação einstein-test (uv, non-root).
FROM python:3.12-slim

# uv (gestor de dependências)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copia o código-fonte ANTES do uv sync (o projeto local precisa de src/)
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh

# Instala o projeto (runtime, sem dev) — o ambiente fica pronto e o `uvicorn`
# roda direto do .venv (sem escrita/rede no runtime como non-root).
RUN uv sync --frozen --no-dev && chmod +x /usr/local/bin/entrypoint.sh

# Usuário non-root para segurança
RUN useradd --create-home --uid 10001 appuser
USER appuser

# O entrypoint aplica as migrations (alembic upgrade head) antes do comando.
# A aplicação usa a factory (fails-fast no startup via validate_settings).
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD [".venv/bin/uvicorn", "einstein_test.main:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]