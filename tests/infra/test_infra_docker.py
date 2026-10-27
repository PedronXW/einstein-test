"""Testes TDD das features F-001/F-009 (infra local: postgres pgvector + minio).

Cada teste valida um critério de aceite (AC-*) usando `docker compose config`
(docker 29.x / compose v5) como fonte de verdade normalizada, além de asserts
estruturais sobre o compose. Rodar da raiz da worktree.
"""

import os
import pathlib
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPOSE = "docker-compose.yml"
INITDB_DIR = ROOT / "docker" / "initdb"


def compose_config() -> str:
    """Roda `docker compose config` na raiz; falha se o YAML for inválido."""
    return subprocess.check_output(
        ["docker", "compose", "config"], cwd=ROOT, text=True
    )


def service_block(cfg: str, service: str) -> str:
    """Extrai o bloco YAML de um serviço do output de `docker compose config`."""
    lines = cfg.splitlines()
    start = None
    indent = None
    for i, line in enumerate(lines):
        if line.strip() == f"{service}:":
            start = i
            indent = len(line) - len(line.lstrip())
            break
    if start is None:
        raise AssertionError(f"servico '{service}' nao encontrado no compose")
    block = [lines[start]]
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        cur = len(line) - len(line.lstrip())
        if cur <= indent:
            break
        block.append(line)
    return "\n".join(block)


@pytest.fixture(scope="module")
def cfg() -> str:
    if not os.path.exists(ROOT / COMPOSE):
        pytest.skip(f"{COMPOSE} deve existir na raiz")
    return compose_config()


# AC-001 — serviço postgres (pgvector, F-009) --------------------------------
def test_ac001_postgres(cfg: str) -> None:
    block = service_block(cfg, "postgres")
    assert "ankane/pgvector" in block, "imagem postgres vetorizado ankane/pgvector"
    assert "pg_isready" in block, "healthcheck pg_isready"
    assert "5432" in block, "porta 5432 publicada"


def test_ac001_postgres_volume(cfg: str) -> None:
    block = service_block(cfg, "postgres")
    assert "pgdata" in block, "volume persistente nomeado pgdata"


def test_ac001_postgres_network(cfg: str) -> None:
    block = service_block(cfg, "postgres")
    assert "infra-net" in block, "servico postgres na rede infra-net"


# AC-002 — serviço minio -----------------------------------------------------
def test_ac002_minio(cfg: str) -> None:
    block = service_block(cfg, "minio")
    assert "minio/minio" in block, "imagem minio/minio"
    assert "/minio/health/live" in block, "healthcheck /minio/health/live"
    assert "9000" in block, "porta 9000 (API) publicada"
    assert "9001" in block, "porta 9001 (console) publicada"


def test_ac002_minio_volume(cfg: str) -> None:
    block = service_block(cfg, "minio")
    assert "minio-data" in block, "volume persistente nomeado minio-data"


def test_ac002_minio_network(cfg: str) -> None:
    block = service_block(cfg, "minio")
    assert "infra-net" in block, "servico minio na rede infra-net"


# AC-003 — banco de teste via init ------------------------------------------
def test_ac003_test_db_init(cfg: str) -> None:
    block = service_block(cfg, "postgres")
    assert "docker-entrypoint-initdb.d" in block, "volume de init do postgres montado"
    initdb = INITDB_DIR / "create-test-db.sh"
    assert initdb.exists(), f"{initdb} deve existir (init do banco de teste)"
    content = initdb.read_text()
    assert "einstein_test" in content, "init deve criar o banco einstein_test"
    assert "ALTER DATABASE einstein_test OWNER TO" in content, (
        "banco de teste deve ter o mesmo user (${POSTGRES_USER})"
    )


# AC-004 — postgres vetorizado (F-009) ---------------------------------------
def test_ac004_pgvector_image(cfg: str) -> None:
    block = service_block(cfg, "postgres")
    assert "ankane/pgvector" in block, "imagem pgvector (ankane/pgvector:latest)"


def test_ac004_pgvector_init_preserved(cfg: str) -> None:
    block = service_block(cfg, "postgres")
    assert "docker-entrypoint-initdb.d" in block, (
        "init do banco de teste preservado (F-001)"
    )
    assert (INITDB_DIR / "create-test-db.sh").exists(), (
        "create-test-db.sh ainda presente"
    )


# AC-001 (F-009) — sem inicialização automática de bucket --------------------
def test_ac001_no_minio_init_service(cfg: str) -> None:
    assert "minio-init" not in cfg, "servico minio-init removido"
    assert "minio/mc" not in cfg, "imagem minio/mc removida"


def test_ac001_minio_still_present(cfg: str) -> None:
    block = service_block(cfg, "minio")
    assert "minio/minio" in block, "MinIO mantido como storage local"


# AC-005 — config válido + network dedicada ----------------------------------
def test_ac005_network_names(cfg: str) -> None:
    assert "name: infra-net" in cfg, "rede dedicada com nome explícito infra-net"


def test_ac005_network_declared(cfg: str) -> None:
    src = (ROOT / COMPOSE).read_text()
    assert "infra-net:" in src, "rede infra-net declarada em networks:"
    assert "infra-net" in cfg


def test_ac005_isolated_from_default(cfg: str) -> None:
    for svc in ("postgres", "minio"):
        block = service_block(cfg, svc)
        assert "infra-net" in block, f"{svc} na rede infra-net"
        assert "default" not in block, f"{svc} nao deve estar na rede default"


def test_ac002_imagens_compose(cfg: str) -> None:
    import re

    images = set(re.findall(r"^\s{4}image:\s*(\S+)", cfg, re.MULTILINE))
    assert images == {"ankane/pgvector:latest", "minio/minio:latest"}, (
        "únicas imagens: ankane/pgvector + minio/minio"
    )