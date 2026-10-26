# F-007 — Service e Controller de Files

## Resumo
Adicionar **FileService** (CRUD orquestrando repositório + storage) e os
**controllers REST** de files com **upload real** via **boto3 + MinIO**
(presigned URL/s3 client contra o bucket do compose F-001), persistindo a
metadata no DB. Rotas aninhadas `/chats/{chat_id}/files` e `/files/{id}` com
`FileRepository.list(chat_id)` (mudança no contrato da F-004).

## Histórias de usuário
- U-001 — **Como** dev, **quero** um `FileService` com `create_file`,
  `get_file`, `list_files`, `delete_file`, **para** orquestrar upload (storage)
  e persistência (metadata).
- U-002 — **Como** usuário da API, **quero** fazer upload de arquivo em
  `POST /chats/{chat_id}/files` (multipart), listar em
  `GET /chats/{chat_id}/files`, e `GET/DELETE /files/{file_id}`,
  **para** gerenciar arquivos de um chat.
- U-003 — **Como** dev, **quero** uma interface de storage testável
  (upload/mock), **para** testar controllers sem depender do MinIO real.
- U-004 — **Como** usuário da API, **quero** `404` (chat/file inexistente) e
  validações (name/url, size >= 0), **para** tratar erros claramente.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `FileRepository.list(chat_id)` alterado (contrato F-004
  atualizado) juntamente com `FileRepositorySQLAlchemy.list(chat_id)` filtrado
  por chat; testes da F-004 atualizados p/ `list(chat_id)`.
- AC-002 — [U-001] `FileService` em `app/services/file.py` com `create_file`
  (marca o upload via storage e persiste metadata), `get_file`, `list_files`,
  `delete_file`; `FileNotFoundError` para file inexistente.
- AC-003 — [U-002/U-003] Interface `Storage` em `app/storage/` com
  `upload(bucket, path, bytes) -> url` (ou presigned); implementação **MinIO**
  via boto3 (`MinioStorage`) e fake/mock p/ testes; storage injetado no service.
- AC-004 — [U-002] Router `app/api/files.py` com `POST /chats/{chat_id}/files`
  (UploadFile multipart + `FileCreate`), `GET /chats/{chat_id}/files`,
  `GET /files/{file_id}`, `DELETE /files/{file_id}`, registrado no app;
  validações (size >= 0, name/url) e 404 chat/file.
- AC-005 — [U-002/U-004] Testes `tests/api/test_files.py` com TestClient
  (SQLite `:memory:` + storage fake) cobrem: upload cria metadata + chama
  storage; list por chat filtra; GET/DELETE por id; 404 (chat e file).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — CRUD completo no FileService. — confirmada
- A-002 — Upload real via boto3 + MinIO do compose (F-001). — confirmada
- A-003 — Upload acontece no `POST /chats/{chat_id}/files` (multipart). — confirmada
- A-004 — `FileRepository.list` muda para `list(chat_id)` (breaking F-004). — confirmada
- A-005 — Storage abstraído (boto3 MinIO real + fake nos testes). — confirmada
- A-006 — 404 chat/file + validações (size >= 0, name/url). — confirmada

## Perguntas em aberto
- (nenhuma)