# F-028 — Cobertura de testes (pytest-cov + relatório no CI)

## Resumo
Adiciona **medição de cobertura** (`pytest-cov`) à suíte, com **target mínimo**
(threshold) para o CI falhar se a cobertura cair abaixo do aceitável, e
**relatório** (terminal + HTML) gerado no pipeline do GitHub Actions. Objetivo:
tornar "cobertura suficiente" uma checagem mecânica, não opinião.

## Histórias de usuário
- U-001 — **Como** dev, **quero** medir a cobertura dos testes localmente
  (`pytest --cov`), **para** saber o quanto do código está coberto.
- U-002 — **Como** dev, **quero** que o CI falhe se a cobertura cair abaixo de
  um **threshold** (fail_under), **para** impedir regressões de cobertura.
- U-003 — **Como** dev, **quero** um **relatório** (terminal + HTML) no CI
  como artefato, **para** revisar áreas cobertas/não.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `pytest-cov` em dev deps; `pyproject.toml`
  (`[tool.coverage.run]` + `[tool.coverage.report]`) com `fail_under` (ex.: 70)
  e `omit` de arquivos de infra (`main.py`, `alembic`, `settings.py` etc. se
  desejado); `uv run pytest --cov=einstein_test` funciona.
- AC-002 — [U-002] CI (`ci.yml`) roda `pytest -m "not integration" --cov=...
  --cov-fail-under=70`; falha se abaixo do threshold.
- AC-003 — [U-003] CI gera relatório `--cov-report=html` + `--cov-report=term`
  e faz upload do HTML como artefato.
- AC-004 — [U-001] Teste local: rodar `pytest --cov` não quebra a suíte; o
  threshold é atingido na suíte atual (se não, ajustamos omit/expectativas
  documentando).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — pytest-cov + fail_under (70% inicial). — confirmada
- A-002 — CI com --cov-fail-under e artefato HTML. — confirmada
- A-003 — Omit de módulos de infra/pouco cobertos quando justificado. — confirmada

## Perguntas em aberto
- (nenhuma)