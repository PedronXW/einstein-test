# F-006 — Service e Controller de Messages

## Resumo
Adicionar o **MessageService** (CRUD completo orquestrando o repositório) e o
**MessageRepository** dedicado (Protocol + SQLAlchemy, como Chat/File da F-004),
além dos **controllers REST** de messages com rotas aninhadas
`/chats/{chat_id}/messages`, Pydantic schemas (`MessageCreate`, `MessageRead`)
e erros `404` (chat ou message inexistente).

## Histórias de usuário
- U-001 — **Como** dev, **quero** um `MessageRepository` dedicado (Protocol +
  impl SQLAlchemy), **para** persistir messages de forma consistente com os
  demais repositórios.
- U-002 — **Como** dev, **quero** um `MessageService` com `create_message`,
  `get_message`, `list_messages`, `delete_message`, **para** orquestrar/validar
  antes de persistir.
- U-003 — **Como** usuário da API, **quero** endpoints aninhados
  `/chats/{chat_id}/messages` (POST cria, GET lista) e GET/DELETE de message por
  id, **para** gerenciar mensagens de um chat via HTTP.
- U-004 — **Como** usuário da API, **quero** `404` com detail ao acessar chat ou
  message inexistente, **para** tratar erros claramente.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `MessageRepository` (Protocol) + `MessageRepositorySQLAlchemy`
  em `app/repositories/message.py` com `create`, `get_by_id`, `list` (filtrado
  por `chat_id`), `delete` (soft); exportado em `app/repositories/`.
- AC-002 — [U-002] `MessageService` em `app/services/message.py` com
  `create_message`, `get_message`, `list_messages`, `delete_message`,
  delegando ao repositório; `MessageNotFoundError` para message inexistente.
- AC-003 — [U-003] Router `app/api/messages.py` com rotas
  `POST /chats/{chat_id}/messages`, `GET /chats/{chat_id}/messages`,
  `GET /messages/{message_id}`, `DELETE /messages/{message_id}`, registrado no
  `create_app`; usa ChatService (404 p/ chat) e MessageService.
- AC-004 — [U-003/U-004] Schemas Pydantic em `app/schemas/message.py`:
  `MessageCreate` (content obrigatório, role opcional) e `MessageRead`
  (id, content, role, criado em); resposta modelada por `response_model`.
- AC-005 — [U-003/U-004] Testes `tests/api/test_messages.py` com TestClient
  (SQLite `:memory:`) cobrem: criar msg em chat existente; listar por chat;
  GET por id (com chat_id no payload); DELETE remove (soft, some da lista);
  **404** para chat inexistente (POST/GET list) e message inexistente
  (GET/DELETE), com `detail`.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — CRUD completo no MessageService. — confirmada
- A-002 — MessageRepository dedicado (Protocol + SQLAlchemy), espelhando F-004. — confirmada
- A-003 — Rotas aninhadas `/chats/{chat_id}/messages`; GET/DELETE por id. — confirmada
- A-004 — Schemas `MessageCreate`/`MessageRead` sem validação fechada de role. — confirmada
- A-005 — 404 para chat inexistente e message inexistente (padrão F-005). — confirmada

## Perguntas em aberto
- (nenhuma)