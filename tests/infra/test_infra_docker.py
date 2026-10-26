"""Testes TDD da feature F-001 (infra local: postgres + minio via docker compose).

Cada teste valida um critério de aceite (AC-*) usando `docker compose config`
(docker 29.x / compose v5) como fonte de verdade normalizada, além de asserts
estruturais sobre o compose. Rodar da raiz da worktree.
"""

import os
import subprocess
import unittest

COMPOSE = "docker-compose.yml"
INITDB_DIR = "docker/initdb"


def compose_config() -> str:
    """Roda `docker compose config` na raiz; falha se o YAML for inválido."""
    return subprocess.check_output(["docker", "compose", "config"], text=True)


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


class TestInfraDocker(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._has_compose = os.path.exists(COMPOSE)
        if not cls._has_compose:
            return
        cls.cfg = compose_config()

    def setUp(self) -> None:
        self.assertTrue(
            self._has_compose, f"{COMPOSE} deve existir na raiz"
        )

    # AC-001 — serviço postgres -------------------------------------------------
    def test_ac001_postgres(self) -> None:
        block = service_block(self.cfg, "postgres")
        self.assertIn("postgres:16-alpine", block, "imagem postgres:16-alpine")
        self.assertIn("pg_isready", block, "healthcheck pg_isready")
        self.assertIn("5432", block, "porta 5432 publicada")

    def test_ac001_postgres_volume(self) -> None:
        block = service_block(self.cfg, "postgres")
        self.assertIn("pgdata", block, "volume persistente nomeado pgdata")

    def test_ac001_postgres_network(self) -> None:
        block = service_block(self.cfg, "postgres")
        self.assertIn("infra-net", block, "servico postgres na rede infra-net")

    # AC-002 — serviço minio -----------------------------------------------------
    def test_ac002_minio(self) -> None:
        block = service_block(self.cfg, "minio")
        self.assertIn("minio/minio", block, "imagem minio/minio")
        self.assertIn("/minio/health/live", block, "healthcheck /minio/health/live")
        self.assertIn("9000", block, "porta 9000 (API) publicada")
        self.assertIn("9001", block, "porta 9001 (console) publicada")

    def test_ac002_minio_volume(self) -> None:
        block = service_block(self.cfg, "minio")
        self.assertIn("minio-data", block, "volume persistente nomeado minio-data")

    def test_ac002_minio_network(self) -> None:
        block = service_block(self.cfg, "minio")
        self.assertIn("infra-net", block, "servico minio na rede infra-net")

    # AC-003 — banco de teste via init ------------------------------------------
    def test_ac003_test_db_init(self) -> None:
        block = service_block(self.cfg, "postgres")
        self.assertIn("docker-entrypoint-initdb.d", block,
                      "volume de init do postgres montado")
        initdb = os.path.join(INITDB_DIR, "create-test-db.sh")
        self.assertTrue(os.path.exists(initdb),
                        f"{initdb} deve existir (init do banco de teste)")
        with open(initdb) as f:
            content = f.read()
        self.assertIn("einstein_test", content,
                      "init deve criar o banco einstein_test")
        self.assertIn("ALTER DATABASE einstein_test OWNER TO", content,
                      "banco de teste deve ter o mesmo user (${POSTGRES_USER})")

    # AC-004 — bucket inicial via minio-init -------------------------------------
    def test_ac004_minio_init(self) -> None:
        block = service_block(self.cfg, "minio-init")
        self.assertIn("minio/mc", block, "servico minio-init com imagem minio/mc")
        self.assertIn("mc mb", block, "minio-init deve rodar mc mb")
        self.assertIn("einstein", block, "bucket padrao einstein")

    def test_ac004_minio_init_depends(self) -> None:
        block = service_block(self.cfg, "minio-init")
        self.assertIn("service_healthy", block,
                      "minio-init deve aguardar minio saudavel")

    # AC-005 — config válido + network dedicada ----------------------------------
    def test_ac005_network_names(self) -> None:
        self.assertIn("infra-net", self.cfg)
        self.assertIn("name: infra-net", self.cfg,
                      "rede dedicada com nome explícito infra-net")

    def test_ac005_network_declared(self) -> None:
        with open(COMPOSE) as f:
            src = f.read()
        self.assertIn("infra-net:", src, "rede infra-net declarada em networks:")

    def test_ac005_isolated_from_default(self) -> None:
        for svc in ("postgres", "minio", "minio-init"):
            block = service_block(self.cfg, svc)
            self.assertIn("infra-net", block, f"{svc} na rede infra-net")
            self.assertNotIn("default", block,
                             f"{svc} nao deve estar na rede default")


if __name__ == "__main__":
    unittest.main()