# models — entidades e mapeamento (SQLAlchemy)

Definem as tabelas e o mapeamento ORM. São a camada mais baixa (não
importam nenhuma outra camada).

## Entidades

- `user.py` — `User` (credenciais, modelo de LLM escolhido).
- `chat.py` — `Chat` (soft delete via `deleted_at`).
- `message.py` — `Message` (histórico do chat, mensagens do usuário e do assistente).
- `file.py` — `File` (arquivo enviado + status da vetorização).
- `file_chunk.py` — `FileChunk` (chunk + vetor `embedding vector(1536)`, índice HNSW).
- `mixin.py` — campos comuns (ids, timestamps).

## Fluxo

```
repositories → models → PostgreSQL + pgvector
```

## Fronteiras

- **Pode**: importar `db.base` (`Base`) e tipos pgvector.
- **Não pode**: importar `repositories`, `services` ou `api`.
