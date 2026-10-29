# vector — vetorização e busca pgvector (RAG)

Pipeline de embeddings e busca por similaridade: transforma arquivos em vetores
e recupera os chunks relevantes por chat.

## Arquivos

- `extractor.py` — extrai texto dos arquivos (tipos suportados em `TEXT_EXTENSIONS`).
- `chunker.py` — divide o texto em chunks.
- `embedder.py` — `Embedder` (Protocol) + `OpenAIEmbedder` (1536 dims) + `FakeEmbedder`.
- `repository.py` — `VectorRepository`: INSERT de chunks e KNN (`<=>`) filtrado por chat (F-011).
- `similarity.py` — re-rank em Python: máx. 2 chunks/arquivo, teto global 12 (F-037).

## Busca

```sql
SELECT ... FROM file_chunks
WHERE file_id IN (arquivos do chat)
ORDER BY embedding <=> :query LIMIT :candidates
```

Índice **HNSW** global (F-017/F-037), usado pelo planner quando vantajoso.

## Fluxo

```
extractor → chunker → embedder → repository (INSERT)
repository (KNN) → similarity (re-rank) → RagService
```
