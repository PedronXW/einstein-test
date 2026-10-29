# F-037 — Busca RAG usa índice HNSW (candidate-pool + re-rank)

## O que foi feito
O `search_similar` do Postgres usava `ROW_NUMBER() OVER (PARTITION BY
file_id ...)` — o planner **não** usa o índice HNSW com essa forma (não é KNN
scan). Agora o caminho Postgres é **candidate-pool KNN + re-rank**:

1. Busca os `file_ids` do chat (`SELECT id FROM files WHERE chat_id=:c AND
   deleted_at IS NULL`).
2. `candidate_limit = min(max(num_files * chunks_per_file, max_chunks),
   MAX_CANDIDATES)` com `MAX_CANDIDATES = 200`.
3. Query KNN: `SELECT * FROM file_chunks WHERE file_id IN (:ids) ORDER BY
   embedding <=> :q LIMIT candidate_limit` — forma que o planner **pode**
   servir com o índice HNSW.
4. Re-rank em Python com o `per_file_top_k_search` (mesmo do fallback SQLite):
   máx `chunks_per_file` por arquivo + teto `max_chunks`, ordem global.

### Comportamento real do planner (validado com EXPLAIN ANALYZE)
- Chat pequeno/médio (filtro seletivo por `file_id`) → o planner prefere o
  **índice FK** (`ix_file_chunks_file_id`) + top-N sort — lê só os chunks do
  chat; correto e rápido.
- Chat **grande** (muitos chunks) → o bitmap+sort fica caro e o planner passa a
  usar o **Index Scan do HNSW** (`ix_file_chunks_embedding_hnsw`).

Ou seja: a forma KNN habilita o HNSW **em escala**, e o plano do índice FK
cobre o caso típico. A antiga query (janela) **nunca** podia usar o HNSW.

### Aproximação do candidate-pool (tradeoff documentado)
O re-rank (`per_file_top_k_search`) tem a semântica exata (máx `chunks_per_file`
por arquivo + teto `max_chunks`) **enquanto o pool KNN contém o top-`chunks_per_file`
de cada arquivo do chat**. Quando um único arquivo domina o top-`MAX_CANDIDATES`
global (chats com muitos chunks), chunks relevantes de outros arquivos podem
ficar de fora do pool e o resultado vira aproximação (comportamento regressado
por `test_ac003_pool_truncation_documents_approximation`). O recall também é
limitado por `candidate_limit` independentemente do plano escolhido pelo
planner.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — `search_similar` (Postgres) usa query KNN (`ORDER BY embedding <=> :q LIMIT` + `file_id IN`), sem `ROW_NUMBER`/janela | PASS | `tests/vector/test_search_similar.py -k 'ac001'` |
| AC-002 | U-001 — `candidate_limit = min(max(num_files*chunks_per_file, max_chunks), MAX_CANDIDATES=200)` | PASS | `tests/vector/test_search_similar.py -k 'ac002'` |
| AC-003 | U-002 — resultado via `per_file_top_k_search` (máx por arquivo + teto, ordem global) | PASS | `tests/vector/test_search_similar.py -k 'ac003'` |
| AC-004 | U-002 — caminho SQLite inalterado; testes existentes de busca seguem verdes | PASS | `tests/vector/test_search_similar.py -k 'ac004'` |

## Veredito mecânico
- `specs proof F-037-hnsw-search` → `PASS` (4/4 ACs).
- `uv run pytest -m "not integration"` → `449 passed, 1 deselected`.
- `uv run ruff check .` → all passed.
- `EXPLAIN ANALYZE` (Postgres local, 8.000 chunks): filtro `file_id IN`
  (chat) → `Bitmap Index Scan on ix_file_chunks_file_id` + `Sort (top-N
  heapsort)`; a forma KNN é reconhecida e o HNSW é usado quando o planner
  julga vantajoso (chat grande) — comportamento documentado no artefato A-004
  da spec.

## Como usar
Nenhuma mudança de API. O RAG (`services/rag/graph.py`) continua chamando
`search_similar(embedding, chat_id, chunks_per_file=2, max_chunks=12)`; o
tamanho do pool KNN é derivado automaticamente (`MAX_CANDIDATES`).

## Arquivos
- `src/einstein_test/vector/repository.py` (`MAX_CANDIDATES`, `_candidate_limit`,
  `_knn_statement`; `search_similar` Postgres → KNN + re-rank)
- `tests/vector/test_search_similar.py` (testes novos por AC + imports limpos)
- `docs/features/F-037-hnsw-search.md` (este)
