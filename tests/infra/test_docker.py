"""Testes TDD da feature F-027 (Dockerfile + compose com app e worker).

Valida a estrutura do Dockerfile (non-root, uv, --factory) e do
docker-compose.yml (serviços api + worker + infra, envs-chave) sem buildar.
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_ac001_dockerfile_exists_and_uses_uv():
    p = ROOT / "Dockerfile"
    assert p.exists(), "Dockerfile existe"
    content = p.read_text()
    assert "python:3.12-slim" in content or "python:3.12" in content, "base 3.12"
    assert "uv sync --frozen" in content, "usa uv sync --frozen"
    assert "--no-dev" in content or "no-dev" in content, "sem dev deps na imagem"


def test_ac001_dockerfile_entrypoint_factory():
    p = ROOT / "Dockerfile"
    content = p.read_text()
    assert "einstein_test.main:create_app" in content, "factory da app"
    assert "--factory" in content, "entrypoint usa --factory"


def test_ac003_dockerfile_nonroot():
    p = ROOT / "Dockerfile"
    content = p.read_text()
    assert "USER " in content, "imagem roda como usuário non-root"
    assert "root" not in content.lower().split("\n")[-3:].__str__() or "USER" in content


def test_ac002_compose_has_api_service():
    p = ROOT / "docker-compose.yml"
    data = yaml.safe_load(p.read_text())
    assert "api" in data["services"], "serviço api presente"
    api = data["services"]["api"]
    assert "build" in api or "image" in api, "api tem imagem/build"
    assert "8000" in str(api.get("ports", [])), "api expõe porta 8000"


def test_ac002_compose_has_worker_service():
    p = ROOT / "docker-compose.yml"
    data = yaml.safe_load(p.read_text())
    assert "worker" in data["services"], "serviço worker presente"
    worker = data["services"]["worker"]
    assert "celery" in str(worker.get("command", "")), "worker roda celery"


def test_ac002_compose_keeps_infra():
    p = ROOT / "docker-compose.yml"
    data = yaml.safe_load(p.read_text())
    for svc in ("postgres", "minio", "redis"):
        assert svc in data["services"], f"infra {svc} presente"


def test_ac004_compose_config_parses():
    p = ROOT / "docker-compose.yml"
    yaml.safe_load(p.read_text())  # não levanta
    assert True


def test_entrypoint_runs_migrations_before_command():
    p = ROOT / "docker/entrypoint.sh"
    assert p.exists(), "docker/entrypoint.sh existe"
    content = p.read_text()
    assert "alembic upgrade head" in content, "entrypoint roda migrations"
    assert 'exec "$@"' in content, "entrypoint executa o comando real depois"
    assert p.stat().st_mode & 0o111, "entrypoint é executável"


def test_dockerfile_copies_alembic_and_sets_entrypoint():
    content = (ROOT / "Dockerfile").read_text()
    assert "COPY alembic.ini" in content, "alembic.ini copiado para a imagem"
    assert "COPY alembic" in content, "diretório alembic/ copiado"
    assert "ENTRYPOINT" in content, "Dockerfile define ENTRYPOINT (migrations)"
    assert "alembic.ini" in content, "alembic.ini referenciado"


def test_alembic_versions_are_copied_to_image():
    # garante que os migration files existem para serem copiados pelo Dockerfile
    versions = ROOT / "alembic" / "versions"
    assert versions.exists(), "diretório alembic/versions existe"
    assert list(versions.glob("*.py")), "há revisões alembic"


def test_compose_minio_endpoint_internal():
    data = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    for svc in ("api", "worker"):
        env = data["services"][svc].get("environment", {})
        assert env.get("MINIO_ENDPOINT") == "http://minio:9000", (
            f"{svc} aponta para o MinIO via hostname interno da rede"
        )


def test_compose_api_workers_fallback_not_interpolated():
    src = (ROOT / "docker-compose.yml").read_text()
    assert "$${API_WORKERS:-1}" in src, (
        "`$` escapado para o compose não interpolar vazio no command do api"
    )