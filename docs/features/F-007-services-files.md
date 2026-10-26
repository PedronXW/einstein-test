# F-007 — Service e Controller de Files

## O que foi feito
**FileService** (CRUD orquestrando upload via storage + persistência de
metadata) e os **controllers REST** de files com **upload real** via
**boto3 + MinIO** (bucket `einstein` do compose F-001). Rotas aninhadas
`/chats/{chat_id}/files` e `/files/{id}`. `FileRepository.list` passou a
receber `chat_id` (breaking da F-004, testes atualizados).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `FileRepository.list(chat_id)` (contrato F-004 atualizado) | PASS | `tests/services/test_file_service.py -k ac001` + `tests/repositories/test_repositories.py -k ac005` |
| AC-002 | U-001 — `FileService` (create com upload, get, list, delete) + `FileNotFoundError` | PASS | `tests/services/test_file_service.py -k ac002` |
| AC-003 | U-002/U-003 — `Storage` Protocol + `MinioStorage` (boto3) + `InMemoryStorage` (fake) | PASS | `tests/services/test_file_service.py -k ac003` |
| AC-004 | U-002 — router `POST/GET /chats/{chat_id}/files` + `GET/DELETE /files/{id}` + validações/404 | PASS | `tests/api/test_files.py -k ac004` |
| AC-005 | U-002/U-004 — upload cria metadata+storage, list por chat, 404 chat/file | PASS | `tests/api/test_files.py -k ac005` |

## Veredito mecânico
`specs proof --strict F-007-services-files` → `PASS` (5/5 ACs). `uv run pytest` → `87 passed`.
Validação viva (uvicorn + postgres + MinIO): `POST /chats/2/files` (multipart)
→ 200 `{"id":1,"name":"f7.txt","url":"s3://einstein/chats/2/f7.txt","size":24}`;
objeto confirmado no bucket via boto3; list por chat retorna.

## Endpoints
- `POST /chats/{chat_id}/files` — upload multipart (UploadFile); 404 se chat inexistente
- `GET /chats/{chat_id}/files` — lista files do chat (filtra por chat e soft-deleted)
- `GET /files/{file_id}` — busca por id; 404 se não existe
- `DELETE /files/{file_id}` — soft delete; 404 se não existe

## Arquivos
- `app/storage/` — `minio.py` (Protocol + MinioStorage boto3), `inmemory.py`, `__init__.py`
- `app/services/file.py` (`FileService`, `FileNotFoundError`)
- `app/repositories/file.py` — `list(chat_id)` atualizado
- `app/api/files.py` (router), `app/schemas/file.py` (`FileRead`)
- `app/main.py` (registro), `pyproject.toml` (+boto3, +python-multipart)
- `tests/services/test_file_service.py`, `tests/api/test_files.py`

## Notas
- Storage abstraído: `Storage` Protocol (upload/delete); `MinioStorage` usa boto3
  contra o MinIO do compose (endpoint/creds via env, default local dev);
  `InMemoryStorage` nos testes (sem rede).
- **Segurança do upload**: chave do objeto gerada server-side
  (`chats/{chat_id}/{uuid}/{basename}`) — nunca usa o filename cru (evita path
  traversal); `name` sanitizado (basename, sem separadores/controle) e truncado
  a 255 chars. Limite de upload `50 MB` → `413`.
- `delete_file` remove o objeto do storage E faz soft delete da metadata.
- `ContentType` enviado no `put_object` (fallback octet-stream).
- `FileNotFound` customizado (não colide com o builtin
  `FileNotFoundError`), consistente com `ChatNotFoundError`/`MessageNotFoundError`.
- `FileRepository.list` agora exige `chat_id` (breaking F-004) — testes da F-004
  atualizados e prova AC-005 da F-004 continua verde.
- Mesma ressalva de segurança das F-005/F-006: endpoints sem auth/owner-scoping —
  pré-requisito para dados sensíveis (feature de autenticação dedicada).