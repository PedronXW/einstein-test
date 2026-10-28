# F-025 — Configuração centralizada (settings) + fails fast no startup

## O que foi feito
Criada uma **fonte única de configuração** (`einstein_test/settings.py`) com
`Settings` (dataclass frozen) como lazy singleton (`get_settings()`), cobrindo
banco/pool, auth, openai/rag, rate limits, celery e retries. O
**`validate_settings()`** valida as obrigatórias (`JWT_SECRET`,
`OPENAI_API_KEY`, `ALLOWED_MODELS`, `DATABASE_URL`) e é chamado no
**`create_app()`** — **falha rápido** no startup em vez de quebrar em runtime.
Módulos-chave (auth, rag/llm adapter, dependencies/pool) passam a ler de
`settings`; `allowed_models()` continua lendo o env por request (call-time,
para refletir mudanças do operador).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `Settings` dataclass frozen + lazy singleton cobrindo as configs | PASS | `tests/infra/test_settings.py -k ac001` |
| AC-002 | U-002 — `validate_settings` (obrigatórias + formato) chamado no create_app (fails fast) | PASS | `tests/infra/test_settings.py -k 'ac002 or ac004'` |
| AC-003 | U-001 — módulos migrados para settings (auth secret/expire, rag model/base/api_key, dependencies database/pool) | PASS | `tests/infra/test_settings.py` |
| AC-004 | U-002 — `validate_settings` testável (aceita válido; rejeita vazios/inválidos) | PASS | `tests/infra/test_settings.py -k ac004` |

## Veredito mecânico
`specs proof --strict F-025-settings` → `PASS` (4/4 ACs). `uv run pytest` →
`305 passed, 1 deselected`.

## Arquivos
- `src/einstein_test/settings.py` (novo) — `Settings`, `get_settings()`,
  `validate_settings()`, `SettingsError`
- `src/einstein_test/main.py` — `create_app` chama `validate_settings()`;
  `main()` usa a factory (remove o `app` global do import)
- `src/einstein_test/api/dependencies.py` — engine/pool via settings
- `src/einstein_test/api/auth.py` — jwt_secret/expire via settings
- `src/einstein_test/services/rag/llm.py` — adapter (api_key/base_url/model)
  via settings
- `tests/infra/test_settings.py` (novo)

## Notas
- `allowed_models()` lê o env por request (não cacheado) — é usada em
  call-time (PATCH e revalidação), então deve refletir mudanças do operador.
- `main()` agora cria o app via `create_app()` (sem `app` global no import),
  então importar o módulo sem config não quebra; o fails-fast acontece na
  chamada a `create_app`/CLI.
- O `create_app` exige env válido → no `pytest`, o conftest seta as
  obrigatórias (JWT_SECRET, OPENAI_API_KEY, ALLOWED_MODELS) para o
  fails-fast passar.