# F-003 — Migrar testes para pytest

## O que foi feito
Suíte de testes migrada de `unittest` para **pytest**: pytest adicionado como
dev-dependency (`[dependency-groups].dev`), os 3 arquivos de teste convertidos
para estilo pytest (funções `test_*` + `assert` + fixtures), e as provas das
features F-001/F-002 atualizadas para o runner novo.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `pytest` em `[dependency-groups].dev` | PASS | `uv run python -c "import tomllib; ..."` (dev-group contém pytest) |
| AC-002 | U-002 — arquivos sem `unittest.TestCase` (api, alembic, infra) | PASS | `! grep -rn 'unittest.TestCase' tests/` |
| AC-003 | U-001 — `uv run pytest` verde na raiz (sem redução) | PASS | `uv run pytest -q` (22 testes) |
| AC-004 | U-003 — trace.tsv de F-001/F-002 com comandos pytest | PASS | comandos re-registrados via `specs prove` |

## Veredito mecânico
`uv run pytest -q` → `22 passed`. `specs proof --strict F-003-tests-pytest` → `PASS`.

## Como usar
```sh
uv run pytest -q            # suíte toda
uv run pytest tests/api     # só a API
uv run pytest tests/infra/test_infra_docker.py -v   # só infra, verboso
```

## Notas
- Preservados os nomes `test_acNNN_*` (rastreabilidade com os ACs de F-001/F-002).
- Fixtures `client`, `cfg` (module-scope) e `alembic_env` substituem setUp/setUpClass.