# F-028 — Cobertura de testes (pytest-cov + relatório no CI)

## O que foi feito
Adicionada **medição de cobertura** com `pytest-cov`:

- `pytest-cov` em dev deps; `[tool.coverage.run]`/`[tool.coverage.report]` no
  pyproject com **`fail_under = 70`**, `omit` de módulos de infra (main,
  settings, middlewares, storage/minio, tasks, logging_setup) e
  `show_missing = true`.
- **CI**: o job `test` roda `pytest -m "not integration" --cov=einstein_test
  --cov-report=term --cov-report=html:htmlcov --cov-fail-under=70` e faz
  **upload do relatório HTML** como artefato.
- Cobertura atual da suíte: **93.39%** (muito acima do threshold).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — pytest-cov + config coverage (fail_under=70, omit) | PASS | `tests/infra/test_coverage.py -k ac001` |
| AC-002 | U-002 — CI com --cov-fail-under=70 | PASS | `tests/infra/test_coverage.py -k ac002` |
| AC-003 | U-003 — CI gera HTML + upload | PASS | `tests/infra/test_coverage.py -k ac003` |
| AC-004 | U-001 — `pytest --cov` não quebra; threshold atingido (93%) | PASS | `tests/infra/test_coverage.py -k ac004` |

## Veredito mecânico
`specs proof --strict F-028-coverage` → `PASS` (4/4 ACs). `uv run pytest` →
`323 passed, 1 deselected`. Cobertura: 93.39%.

## Arquivos
- `pyproject.toml` (+`pytest-cov`, `[tool.coverage.*]`)
- `.github/workflows/ci.yml` (--cov no job test, artefato HTML)
- `tests/infra/test_coverage.py` (novo)

## Notas
- O `omit` foca em módulos de infra (entrypoint, config, middlewares, storage
  real, tasks, logging) — áreas com cobertura baixa por natureza de integração
  ou trivial. O núcleo (models/repositories/services/api/vector) fica coberto.
- O CI falha (exit != 0) se a cobertura cair abaixo de 70% — impede regressões
  sem medição.