# F-017 — Índice HNSW no pgvector para busca vetorial

## Resumo
Cria um **índice HNSW** na coluna `file_chunks.embedding` usando o operador de
similaridade de cosseno (`vector_cosine_ops`) via migration Alembic. A busca
`search_similar` (cosine `<=>`) passa a usar o índice, reduzindo a busca de
O(n) para O(log n) aproximada conforme os chunks acumulam — otimização
preventiva para chats com muitos arquivos.

## Histórias de usuário
- U-001 — **Como** dev, **quero** um índice HNSW em `embedding`, **para** manter
  a busca RAG rápida mesmo com muitos chunks por chat.
- U-002 — **Como** dev, **quero** que a busca (`search_similar`) continue
  retornando os mesmos chunks (função preservada), **para** não mudar o
  comportamento do RAG.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] Migration Alembic adiciona índice HNSW:
  `CREATE INDEX ON file_chunks USING hnsw (embedding vector_cosine_ops)`.
  `alembic upgrade head --sql` emite o comando; `idx` nomeada
  (`ix_file_chunks_embedding_hnsw`).
- AC-002 — [U-002] `search_similar` (pgvector `<=>`) continua funcionando após
  a migration (teste com sqlite/fallback Python permanece verde); nenhuma
  mudança de contrato.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Índice HNSW com `vector_cosine_ops`. — confirmada
- A-002 — Prova via migration (--sql) + busca segue ok (sem postgres no CI). — confirmada

## Perguntas em aberto
- (nenhuma)