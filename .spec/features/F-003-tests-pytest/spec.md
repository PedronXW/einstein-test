# F-003 — Migrar testes para pytest

## Resumo
Migrar a suíte de testes do projeto de `unittest` para **pytest**: adicionar
pytest como dependência de dev, converter os 3 arquivos de teste existentes para
estilo pytest (assert plano/functions, fixtures), e atualizar os comandos de
prova registrados (trace.tsv) das features F-001 e F-002 para usar o pytest.

## Histórias de usuário
- U-001 — **Como** dev, **quero** rodar a suíte com `uv run pytest`,
  **para** ter um runner moderno com melhor saída, seleção e fixtures.
- U-002 — **Como** dev, **quero** que os testes existentes sejam convertidos
  para estilo pytest (funções `test_*` + `assert`), **para** eliminar o
  boilerplate de `unittest.TestCase` e usar idiomática do pytest.
- U-003 — **Como** dev, **quero** que as provas mecânicas das features passadas
  (F-001 infra, F-002 fastapi+alembic) continuem registradas/comandos pytest,
  **para** o gate da spec continuar auditável.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `pytest` declarado como dependência de dev
  (`[dependency-groups].dev` no pyproject.toml) e instalável via `uv`.
- AC-002 — [U-002] Arquivos de teste convertidos para pytest (funções `test_*`
  sem classes `unittest.TestCase`): `tests/api/test_hello.py`,
  `tests/alembic/test_alembic_config.py` e `tests/infra/test_infra_docker.py`.
- AC-003 — [U-001] `uv run pytest` roda verde na raiz (exit 0), cobrindo todos
  os testes antes cobertos por unittest (API, Alembic, infra) sem redução.
- AC-004 — [U-003] Comandos no `trace.tsv` de F-001 e F-002 atualizados para
  `uv run pytest ...` (mesmos critérios/provas, runner novo).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — pytest entra como dev-dependency (não runtime), num grupo `.dev`. — confirmada
- A-002 — Migrar testes preservando nomes `test_acNNN_*` (rastreabilidade com ACs). — confirmada
- A-003 — fixtures pytest podem substituir `setUp/setUpClass` de unittest. — confirmada

## Perguntas em aberto
- (nenhuma)