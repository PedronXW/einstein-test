# F-037 — Busca RAG usa índice HNSW (candidate-pool + re-rank)

## Resumo
O índice HNSW `ix_file_chunks_embedding_hnsw` existe no banco, mas o
`search_similar` do Postgres usa `ROW_NUMBER() OVER (PARTITION BY file_id
...)` — o planner **não** usa o índice (não é KNN scan). Esta feature troca o
caminho Postgres para **candidate-pool KNN + re-rank em Python**: busca os
candidatos mais próximos via `ORDER BY embedding <=> :q LIMIT :L` com
`file_id IN (arquivos do chat)` (formato que o planner reconhece como scan do
HNSW), e aplica o `per_file_top_k_search` (mesmo do fallback SQLite) para
manter a semântica (máx `chunks_per_file` por arquivo + teto `max_chunks`).

## Histórias de usuário
- U-001 — **Como** desenvolvedor, **quero** que a busca RAG use o índice HNSW,
  **para** acelerar o retrieve quando há muitos chunks.
- U-002 — **Como** usuário, **quero** que o resultado da busca mantenha a
  semântica atual (top chunks por arquivo + teto global), **para** respostas
  coerentes e diversidade entre arquivos.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] `search_similar` (Postgres) usa query KNN:
  `ORDER BY embedding <=> :q LIMIT candidate_limit` com `file_id IN` (arquivos
  do chat) — sem `ROW_NUMBER`/janela; forma reconhecida como scan do HNSW.
- AC-002 — [U-001] `candidate_limit = min(max(num_files * chunks_per_file,
  max_chunks), MAX_CANDIDATES)` com `MAX_CANDIDATES = 200`.
- AC-003 — [U-002] Resultado final via `per_file_top_k_search` (re-rank em
  Python): máx `chunks_per_file` por arquivo + teto `max_chunks`, ordem global
  por similaridade.
- AC-004 — [U-002] Caminho SQLite **inalterado**; testes existentes de busca
  por similaridade seguem verdes (semântica preservada).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Candidate-pool KNN + re-rank reproduz a semântica exata nos casos
  normais; em caso patológico (um arquivo domina o top de candidatos) pode
  haver aproximação, mitigada por `candidate_limit = num_files * chunks_per_file`
  e cap `MAX_CANDIDATES` — confirmada.
- A-002 — `MAX_CANDIDATES = 200` é tuning; mora no módulo do repositório
  vetorial (fonte única) — confirmada.
- A-003 — Sem migration nova: o índice HNSW já existe no banco — confirmada.
- A-004 — `WHERE file_id IN (lista) ORDER BY embedding <=> :q LIMIT :L` torna
  o HNSW **usável** pelo planner quando vantajoso (chat com muitos chunks —
  validado por `EXPLAIN ANALYZE`); com filtro seletivo de arquivos o planner
  prefere o índice FK (`ix_file_chunks_file_id`) + top-N sort, que é correto e
  rápido (sem tradeoff de recall) — confirmada.

## Perguntas em aberto
- (nenhuma)
