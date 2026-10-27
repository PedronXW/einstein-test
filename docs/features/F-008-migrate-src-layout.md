# F-008 — Migrar app/ para src/einstein_test (src-layout)

## O que foi feito
Pacote da aplicação movido de `app/` (raiz) para `src/einstein_test/`
(src-layout padrão do `uv_build`), com todos os imports reescritos
(`from app.` → `from einstein_test.`) em `src/`, `tests/` e `alembic/`.
Removido o script stub `einstein-test = "einstein_test:main"` do pyproject
(nada o usava). El error "Expected a Python module at: src/einstein_test/__init__.py"
desaparece porque ahora el package vive en `src/einstein_test/`.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `app/` movido a `src/einstein_test/`; dir `app/` removido | PASS | `test ! -d app && test -d src/einstein_test && test -f src/einstein_test/main.py` |
| AC-002 | U-001 — imports reescritos (sin `from app.`) en src/tests/alembic | PASS | `! grep -rnE 'from app.|import app.' src tests alembic` |
| AC-003 | U-002 — package resuelve desde `src/` (import real) | PASS | `import einstein_test.main` → archivo en `src/einstein_test/` |
| AC-004 | U-002 — pytest verde, alembic offline OK, uvicorn carga | PASS | `uv run pytest` + `alembic upgrade --sql` + `from einstein_test.main import app` |

## Veredito mecânico
`specs proof --strict F-008-migrate-src-layout` → `PASS` (4/4 ACs).
`uv run pytest` → `93 passed`. `uv run alembic upgrade head --sql` → exit 0.
`uv build` → wheel gerado (`dist/einstein_test-0.1.0-*.whl`).
`uv run python -c "from einstein_test.main import app; print(app.title)"` → `einstein-test`.

## Arquivos
- `src/einstein_test/` — antigua `app/` (api/, db/, models/, repositories/,
  schemas/, services/, storage/, main.py) com imports `einstein_test.`
- `tests/`, `alembic/env.py` — imports atualizados
- `pyproject.toml` — removido `[project.scripts]` (stub)
- `app/` — eliminado

## Notas
- src-layout estándar del `uv_build`: `uv run pytest`/`uv build`/`uv run uvicorn`
  funcionan sin el stub `uv init` que tenía `main()`.
- El `__init__.py` de `src/einstein_test/` quedó vacío (es el package, no necesita
  contenido); el código real está en `einstein_test.main` y subpaquetes.
- Uvicorn: `uv run uvicorn einstein_test.main:app`.