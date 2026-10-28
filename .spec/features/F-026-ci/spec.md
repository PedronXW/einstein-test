# F-026 — CI (GitHub Actions) — testes automáticos em push/PR

## Resumo
Cria um pipeline de **CI no GitHub Actions** que roda a suíte de testes
(unitários + specs), valida o schema (alembic), e aplica o `ruff`/lint básico
em push/PR. A integração (marker `integration`) fica excluída por padrão (sem
chave/infra). Objetivo: "pronto = exit code" também no repositório, não só no
ambiente local.

## Histórias de usuário
- U-001 — **Como** dev, **quero** que a suíte de testes rode automaticamente em
  push/PR no GitHub Actions, **para** detectar regressões antes do merge.
- U-002 — **Como** dev, **quero** que a integração (`-m integration`) fique
  fora do CI padrão (sem credenciais), **para** não falhar por falta de chave.
- U-003 — **Como** dev, **quero** validação do Alembic (schema consistente) e
  lint básico no CI, **para** não quebrar migrations/estilo silenciosamente.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `.github/workflows/ci.yml`: job `test` com uv sync +
  `pytest -m "not integration"` em Ubuntu (python 3.12); dispara em push e
  pull_request; artefato do relatório de testes (se houver).
- AC-002 — [U-002] O job **não** roda `-m integration` (excluído); se um
  workflow de integração existir, é separado e manual (`workflow_dispatch`).
- AC-003 — [U-003] Job roda `alembic check` (schema) e `ruff check` (lint) —
  falha se drift/erro de estilo.
- AC-004 — [U-001] Verificação mecânica local: o workflow pode ser validado por
  teste que confere a presença/estrutura do `ci.yml` (não executa o Actions).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — GitHub Actions no `.github/workflows/ci.yml`. — confirmada
- A-002 — uv + pytest -m "not integration" + alembic check + ruff. — confirmada
- A-003 — Integração fora do CI padrão. — confirmada

## Perguntas em aberto
- (nenhuma)