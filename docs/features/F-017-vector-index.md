# F-017 — Índice HNSW no pgvector para busca vetorial

## O que foi feito
A coluna `file_chunks.embedding` (vector(1536)) ganhou um **índice HNSW** com
operador de similaridade de cosseno (`vector_cosine_ops`) via migration
Alembic. A busca `search_similar` (cosine `<=>`) do RAG passa a usar o índice,
reduzindo a busca de O(n) para O(log n) aproximada conforme os chunks
acumulam — otimização preventiva para chats com muitos arquivos.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — migration `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)` (nome `ix_file_chunks_embedding_hnsw`); `--sql` emite | PASS | `tests/migrations/test_vector_index.py -k ac001` |
| AC-002 | U-002 — `search_similar` continua funcionando após a migration (busca preservada, fallback sqlite/`per_file_top_k_search` intacto) | PASS | `tests/migrations/test_vector_index.py -k ac002` |

## Veredito mecânico
`specs proof --strict F-017-vector-index` → `PASS` (2/2 ACs). `uv run pytest` →
`252 passed`.

## Arquivos
- `alembic/versions/601b3bb88689_hnsw_index_on_file_chunks_embedding.py`
- `tests/migrations/test_vector_index.py` (novo)

## Notas
- Índice HNSW é de **aproximação** (alta precisão com top_k baixo); ingestão
  um pouco mais lenta — aceitável na escala atual.
- O índice foi criado no postgres real (verificado via `\di`). Downgrade remove
  o índice com `DROP INDEX`.
- Nenhuma mudança de contrato: a busca continua igual.