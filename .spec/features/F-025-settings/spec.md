# F-025 — Configuração centralizada (settings) + fails fast no startup

## Resumo
Hoje as configs são lidas de `os.getenv` espalhadas (`dependencies.py`,
`rag/llm.py`, `api/auth.py`, `middleware/rate_limit.py`, `tasks/`), sem uma
fonte única nem validação no startup — um operador pode subir a API com
`JWT_SECRET`/`OPENAI_API_KEY`/`ALLOWED_MODELS` ausentes e só descobrir em
runtime. Esta feature cria um **`settings.py` central** (dataclass/frozen com
valores via env) e uma **validação no startup** (`create_app`/CLI) que
**falha rápido** se configs obrigatórias estiverem ausentes/inválidas — sem
mudar o comportamento dos endpoints.

## Histórias de usuário
- U-001 — **Como** dev/operador, **quero** uma única fonte de configuração
  (`einstein_test.settings.Settings`), **para** entender/validar todas as
  variáveis num lugar só.
- U-002 — **Como** operador, **quero** que o app **falhe rápido** no startup se
  `JWT_SECRET`/`OPENAI_API_KEY`/`ALLOWED_MODELS`/`DATABASE_URL` estiverem
  ausentes ou inválidos, **para** não operar com config quebrada.
- U-003 — **Como** dev, **quero** que os módulos consumam `Settings` (em vez de
  `os.getenv` direto), **para** centralizar defaults e documentar.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `einstein_test/settings.py` com `@dataclass(frozen=True)`
  `Settings` (lazy singleton `get_settings()`/`settings`) cobrindo: `database_url`,
  `jwt_secret`, `access_token_expire_minutes`, `openai_api_key`, `openai_base_url`,
  `openai_chat_model`, `allowed_models`, `log_level`, pool (size/overflow/timeout),
  rate limits, celery broker/backend, retries (vectorize/llm). Lê env e `.env`.
- AC-002 — [U-002] `validate_settings(s)` valida: `jwt_secret` não vazio,
  `openai_api_key` não vazio, `allowed_models` não vazio, `database_url` com
  `postgresql://`/`sqlite://`; raises `SettingsError` com lista de problemas.
  Chamado no `create_app` e no entrypoint (`main.main`) → **falha rápido**.
- AC-003 — [U-001] Módulos passam a ler de `settings` (no mínimo: auth secret/
  expire, rag allowed_models/model/base_url/api_key/retries, dependencies
  database/pool, rate_limit limites, tasks celery/retries) — sem quebrar a
  suíte (comportamento igual).
- AC-004 — [U-002] `validate_settings` é testável: aceita env válido, rejeita
  `jwt_secret`/`openai_api_key`/`allowed_models` vazios, rejeita
  `database_url` inválido; testes com override.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — `Settings` dataclass frozen + lazy singleton (`get_settings()`). — confirmada
- A-002 — `validate_settings` no `create_app`/entrypoint (fails fast). — confirmada
- A-003 — Módulos migram para `settings` sem mudar comportamento. — confirmada
- A-004 — Configs obrigatórias: jwt_secret, openai_api_key, allowed_models, database_url. — confirmada

## Perguntas em aberto
- (nenhuma)