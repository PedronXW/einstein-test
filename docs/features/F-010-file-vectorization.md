# F-010 — Vetorização de arquivos (pgvector + embeddings)

## O que foi feito
Ao adicionar um arquivo (upload via `POST /chats/{chat_id}/files`), o
**FileService** agora extrai o texto (texto puro `.txt/.md/...` ou **PDF** via
**pypdf**), divide em chunks por tamanho de caracteres (default 1000/200) e
**vetoriza** cada chunk com embeddings **Cohere** (`cohere/embed-v4.0`,
dimensão 1024) via endpoint OpenAI-compatível
(`https://spillway.ensinoeinstein.com/openai/v1`, configurável em `.env`),
persistindo os vetores no **pgvector** (tabela `file_chunks`)
e guardando no model `File` os **identificadores** `chunk_ids` (lista de ids
dos chunks) e `vector_reference` (UUID do documento vetorial).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `Embedder` Protocol + `OpenAIEmbedder` (cohere/embed-v4.0 via `.env`, 1024) + `FakeEmbedder` determinístico | PASS | `tests/vector/test_embedder.py` |
| AC-002 | U-002 — `TextExtractor`: `.txt/.md` (utf-8) + PDF via pypdf; sem texto → `[]` | PASS | `tests/vector/test_extractor_chunker.py -k ac002` |
| AC-003 | U-002 — `TextChunker` (chunk_size=1000, overlap=200) | PASS | `tests/vector/test_extractor_chunker.py -k ac003` |
| AC-004 | U-003 — tabela `file_chunks` (pgvector vector(1024)) + `VectorRepository` (insert/get/delete) | PASS | `tests/vector/test_vector_repository.py` |
| AC-005 | U-004 — `File.chunk_ids` (JSONB) + `vector_reference` (UUID); `FileService.create_file` popula | PASS | `tests/models/test_file_vectorization.py` + `tests/services/test_file_vectorization.py` |
| AC-006 | U-005 — upload síncrono vetoriza; `FileRead` expõe `chunk_ids`/`vector_reference` | PASS | `tests/api/test_file_vectorization.py` |
| AC-007 | U-006 — migration Alembic: `CREATE EXTENSION vector`, `file_chunks`, colunas novas em `files` | PASS | `tests/alembic/test_file_vectorization.py` |
| AC-008 | U-001/U-005 — service + API + extractor PDF com fixture | PASS | `tests/services/test_file_vectorization.py` + `tests/api/test_file_vectorization.py` |

## Veredito mecânico
`specs proof --strict F-010-file-vectorization` → `PASS` (8/8 ACs). `uv run pytest` → `148 passed`.

## Correções do deep review
- Produção usa `OpenAIEmbedder` (Cohere cohere/embed-v4.0 via `get_embedder()` lazy); `FakeEmbedder` só nos testes.
- Migration com `server_default='[]'` para `chunk_ids` (segura em tabela populada).
- `TextChunker` valida `0 <= overlap < chunk_size` (evita loop infinito).
- `insert_chunks` em bulk com um único commit (sem N+1).
- `OpenAIEmbedder` reutiliza o client e valida dimensão do embedding.
- Limite `MAX_CHUNKS=500` por upload (evita DoS por chunks ilimitados).
- Endpoint `upload_file` síncrono (threadpool do FastAPI, sem bloquear o event loop).
- `upload_file` usa `file.file.read(MAX+1)` para validar o limite antes de alocar.

## Mudanças na API
- `FileRead` ganhou `chunk_ids: list[int]` e `vector_reference: str | None`.
- Upload (`POST /chats/{chat_id}/files`) agora vetoriza de forma síncrona.

## Arquivos
- `src/einstein_test/vector/` — `embedder.py` (Protocol + OpenAI + Fake),
  `extractor.py` (pypdf), `chunker.py`, `repository.py` (pgvector), `__init__.py`
- `src/einstein_test/models/file_chunk.py` (`FileChunk`), `models/file.py`
  (+`chunk_ids`, `vector_reference`)
- `src/einstein_test/repositories/file.py` (+`update_chunk_ids`),
  `repositories/__init__.py` (+`VectorRepository`)
- `src/einstein_test/services/file.py` (vetorização no `create_file`/`delete_file`)
- `src/einstein_test/schemas/file.py` (`FileRead`), `src/einstein_test/api/files.py`
- `alembic/versions/c5eda6f1d350_file_vectorization_pgvector.py`
- `pyproject.toml` (+`openai`, +`pypdf`, +`pgvector`)
- `tests/vector/`, `tests/models/test_file_vectorization.py`,
  `tests/services/test_file_vectorization.py`, `tests/api/test_file_vectorization.py`,
  `tests/alembic/test_file_vectorization.py`

## Notas
- `FakeEmbedder` gera vetores determinísticos (hash do texto) com 1024 dims,
  usado nos testes (sem rede/chave).
- A migration adiciona `CREATE EXTENSION IF NOT EXISTS vector` e a tabela
  `file_chunks` com `embedding VECTOR(1024)`; colunas `chunk_ids` (JSONB) e
  `vector_reference` em `files`.
- Configuração do embedder em `.env` (não versionado): `OPENAI_API_KEY`,
  `OPENAI_BASE_URL=https://spillway.ensinoeinstein.com/openai/v1`,
  `OPENAI_MODEL=cohere/embed-v4.0`, `OPENAI_EMBEDDING_DIM=1024`;
  `.env.example` versionado com o modelo.
- `vector_reference` é um UUID gerado por arquivo, identificando o documento
  vetorial; `chunk_ids` são os ids na tabela `file_chunks` (acesso às infos).
- Banco de vetores é o pgvector do postgres do compose (F-009).