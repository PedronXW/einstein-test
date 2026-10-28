# F-024 — Testes de integração opcionais (marker integration)

## O que foi feito
Criada uma suíte de **testes de integração opcionais** que usa o provedor real
(OpenAI-compatível) para validar o fluxo ponta-a-ponta:

- **Marker `integration`** registrado no `pyproject.toml` e **excluído do CI
  padrão** (`addopts = -m "not integration"`).
- **`tests/integration/`**: fixture `integration_available` que **skipa**
  graciosamente quando `RUN_INTEGRATION != "1"` ou `OPENAI_API_KEY` ausente —
  nunca falha o `pytest` local.
- **`test_rag_end_to_end`**: app real (postgres do ambiente) → upload de
  arquivo → aguarda vetorização `ready` → pergunta → SSE streaming com
  `[DONE]` e `assistant` salva.
- **`test_integration_config`**: valida o marker/addopts e o skip gracioso.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-002 — marker `integration` + `addopts -m "not integration"`; suíte padrão verde | PASS | `tests/integration/test_integration_config.py -k ac001` |
| AC-002 | U-003 — conftest/fixture skipa sem chave/RUN_INTEGRATION; testes marcados | PASS | `tests/integration/test_integration_config.py -k ac002` |
| AC-003 | U-001 — `test_rag_end_to_end` (upload→ready→pergunta→SSE) skipa sem infra | PASS | `pytest -m integration tests/integration/` |
| AC-004 | U-002 — CI padrão roda sem integração (296 passed, 1 deselected) | PASS | `pytest -q` |

## Veredito mecânico
`specs proof --strict F-024-integration-tests` → `PASS` (4/4 ACs). `uv run pytest` →
`296 passed, 1 deselected`.

## Como rodar a integração
```bash
# infra de pé (postgres/minio/redis) + chave real
RUN_INTEGRATION=1 uv run pytest -m integration tests/integration/
```

## Arquivos
- `pyproject.toml` — `markers` + `addopts`
- `tests/integration/test_rag_end_to_end.py` (end-to-end real, marcado
  `integration`)
- `tests/integration/test_integration_config.py` (valida marker/addopts/skip)

## Notas
- Sem `RUN_INTEGRATION`/chave, a integração **skipa** (não falha) — o CI e o
  `pytest` local continuam verdes.
- O teste end-to-end usa o banco real (`DATABASE_URL`) e o storage em memória
  (o upload real pode ser adaptado para MinIO se desejado).