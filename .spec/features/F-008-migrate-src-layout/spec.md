# F-008 — Migrar app/ para src/einstein_test (src-layout)

## Resumo
Migrar o pacote da aplicação de `app/` (raiz) para `src/einstein_test/`
(src-layout padrão do uv_build), reescrevendo os imports (`from app.` →
`from einstein_test.`) em `src/`, `tests/` e `alembic/`. Remove o stub
`src/einstein_test/__init__.py` (de `uv init`) que hoje coexiste com a pasta
`app/` sem conteúdo próprio.

## Histórias de usuário
- U-001 — **Como** dev, **quero** o pacote da aplicação em `src/einstein_test/`
  (src-layout), **para** que o `uv build` produza o package correto sem o stub
  `uv init` e sem o erro "Expected a Python module at: src/einstein_test/__init__.py".
- U-002 — **Como** dev, **quero** que `uv run pytest`, `uv run alembic` e
  `uv run uvicorn` funcionem após a migração (imports coerentes), **para** nada
  quebrar no dev de rotina.

## Critérios de aceite
- AC-001 — [U-001] Pacote `app/` movido para `src/einstein_test/` (mesma
  árvore: api/, db/, models/, repositories/, schemas/, services/, storage/,
  main.py); diretório `app/` removido.
- AC-002 — [U-001] Todos os imports `from app.` / `import app.` reescritos
  para `from einstein_test.` / `import einstein_test.` em `src/`, `tests/` e
  `alembic/`; nada referencia mais `app.` (grep vazio).
- AC-003 — [U-002] `uv build`/env resolve o package `einstein_test` a partir de
  `src/` e não há mais o erro de módulo esperado; `pyproject.toml` mantém
  `uv_build` e o entrypoint (se aplicável) aponta para `einstein_test:...`.
- AC-004 — [U-002] `uv run pytest` (suíte completa) retorna verde após a
  migração; `uv run alembic upgrade head --sql` (offline) executa com o novo
  import; `uv run uvicorn einstein_test.main:app` carrega o app.

## Suposições
- A-001 — src-layout padrão do uv_build: `src/einstein_test/`. — confirmada
- A-002 — Entrypoint de script do pyproject (se mantido) passa a usar
  `einstein_test.main` ou é removido — nada usa o stub `main()` do uv init. — confirmada

## Perguntas em aberto
- (nenhuma)