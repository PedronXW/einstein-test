#!/bin/sh
# Entrypoint da imagem: garante o schema aplicando as migrations (alembic)
# antes de executar o comando da aplicação (api ou worker).
#
# Com `depends_on` healthy do postgres, o banco está de pé; mas em envs sem
# compose (docker run puro) pode subir junto — então tentamos com retry.
set -eu

MIGRATE_MAX_RETRIES="${MIGRATE_MAX_RETRIES:-10}"
MIGRATE_RETRY_DELAY="${MIGRATE_RETRY_DELAY:-2}"

run_migrations() {
  echo "[entrypoint] aplicando migrations (alembic upgrade head)..."
  .venv/bin/alembic upgrade head
}

attempt=1
until run_migrations; do
  if [ "$attempt" -ge "$MIGRATE_MAX_RETRIES" ]; then
    echo "[entrypoint] migrations falharam após $MIGRATE_MAX_RETRIES tentativas" >&2
    exit 1
  fi
  echo "[entrypoint] banco ainda indisponível? (tentativa $attempt/$MIGRATE_MAX_RETRIES em ${MIGRATE_RETRY_DELAY}s)"
  attempt=$((attempt + 1))
  sleep "$MIGRATE_RETRY_DELAY"
done

echo "[entrypoint] migrations ok — iniciando: $*"
exec "$@"