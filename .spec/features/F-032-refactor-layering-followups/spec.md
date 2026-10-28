# F-032 — Refactor layering follow-ups

## Resumo
Auditoria geral pós-F-031 encontrou dois resíduos de layering na regra de ouro
`controller(api) -> service -> repository -> model`:

1. **Regra de negócio no controller**: `MAX_HISTORY = 10` (política de histórico
   do RAG) e o slice `[-MAX_HISTORY:]` vivem em `api/messages.py`. A prova
   estrutural de F-031 (`test_layering_rule.py`) só cobre
   `MAX_UPLOAD_SIZE`/`MAX_FILES_PER_BATCH`/`DEFAULT_USER_MODEL`/`FILE_STATUS_*` —
   `MAX_HISTORY` passou batido.
2. **Dependência reversa infra→api**: `middleware/rate_limit.py` e
   `middleware/logging_middleware.py` importam `decode_token` de
   `einstein_test.api.auth` (camada controller), arrastando repos/services/models
   para dentro do infra. A F-031 já eliminou `tasks→api`; falta fazer o mesmo
   para o middleware movendo os helpers JWT para `security.py`.

Esta feature é refactor estrutural: mesma API HTTP, mesmos dados, mesmos
contratos — nenhuma mudança de comportamento externo.

## Histórias de usuário
- U-001 — **Como** dev, **quero** que regras de domínio (limites de histórico
  do RAG) vivam no service e sejam importadas pelo controller, **para** que o
  controller não carregue política de negócio e a prova estrutural de layering
  cubra a constante.
- U-002 — **Como** dev, **quero** que helpers JWT (`create_access_token`/
  `decode_token`) vivam em `security.py` (junto do bcrypt, mesma moradia de
  política criptográfica), **para** que middleware/outros callers importem de
  `security`, nunca da camada `api`.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `MAX_HISTORY` deixa de ser definido em `api/messages.py`;
  passa a ser exposto por um service (`MessageService` vira fonte única) e o
  controller apenas o importa; `test_layering_rule.py` passa a rejeitar
  `MAX_HISTORY =` no controller.
- AC-002 — [U-002] `create_access_token`/`decode_token` movem para
  `einstein_test.security`; `api/auth.py` reutiliza de lá (contrato do
  `get_current_user` preservado); `middleware/rate_limit.py` e
  `middleware/logging_middleware.py` importam de `security`, nunca de
  `einstein_test.api`; prova estrutural confirma que o middleware não depende
  da camada api.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — `decode_token` mantém seu contrato atual (levanta 401 via
  `HTTPException`) mesmo morando em `security`; `security` passa a depender de
  FastAPI para a exceção, mas sem dependência de `api` — aceitável, pois os
  middlewares já toleram exceção de token inválido com try/except.
- A-002 — Mudança 100% estrutural: nenhum contrato HTTP/dados muda (mesmos
  endpoints, status, schemas e colunas).

## Perguntas em aberto
- Q-001 — Onde fica a fonte única de `MAX_HISTORY`? `MessageService`
  (`services/message.py`), pois é política da camada de mensagens/RAG, não de
  storage/config — resolvida.
- Q-002 — `decode_token` levanta `HTTPException(401)`; movê-lo para `security`
  faz `security` importar `fastapi`. Aceitável? Sim — permanece infra de borda
  HTTP e elimina o acoplamento middleware→api — resolvida.