# F-010 — Vetorização de arquivos (pgvector + embeddings)

## Resumo
Quando um arquivo for adicionado (`FileService.create_file`), extrair o texto
(plain text ou PDF via pypdf), dividir em chunks por tamanho de caracteres e
vetorizar cada chunk com **Cohere embeddings** (`cohere/embed-v4.0`, dimensão
1024) via endpoint OpenAI-compatível (`https://spillway.ensinoeinstein.com/openai/v1`)
configurável em `.env`, persistindo os vetores no **pgvector** (postgres do compose) e
guardando no model `File` do banco relacional os **identificadores** (lista de
`chunk_ids` + `reference` ao documento vetorizado) para acessar as infos
vetoriais.

## Histórias de usuário
- U-001 — **Como** dev, **quero** uma interface `Embedder` abstraída com
  implementação real (Cohere `cohere/embed-v4.0` via endpoint OpenAI-compatível)
  e fake determinístico para testes, **para** gerar embeddings sem depender de
  rede nos testes.
- U-002 — **Como** dev, **quero** extrair texto de arquivos (texto puro e PDF
  via pypdf) e dividir em chunks por tamanho de caracteres, **para** vetorizar
  conteúdo processável.
- U-003 — **Como** dev, **quero** persistir os vetores (chunks) no **pgvector**
  com um repositório vetorial dedicado, **para** consultar similaridade depois.
- U-004 — **Como** dev, **quero** que o model `File` guarde `chunk_ids` e
  `vector_reference` apontando para os chunks no banco vetorial, **para**
  acessar as infos vetoriais de um arquivo.
- U-005 — **Como** usuário da API, **quero** que ao fazer upload de um arquivo
  (texto ou PDF) ele seja vetorizado de forma **síncrona** dentro do
  `POST /chats/{chat_id}/files`, **para** ter os vetores disponíveis na hora.
- U-006 — **Como** dev, **quero** migration Alembic criando a extensão pgvector,
  a tabela vetorial (`file_chunks`) e os campos novos em `files`, **para** o
  schema convergir no postgres real.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] Protocol `Embedder` em `src/einstein_test/vector/` com
  `embed(texts: list[str]) -> list[list[float]]`; `OpenAIEmbedder`
  (config via `.env`: `OPENAI_API_KEY`, `OPENAI_BASE_URL`
  `https://spillway.ensinoeinstein.com/openai/v1`, model `cohere/embed-v4.0`,
  dimensão 1024) e `FakeEmbedder` determinístico (hash → vetor de 1024 dims)
  para testes.
- AC-002 — [U-002] `TextExtractor` extrai texto de `.txt`/`.md` (decodifica
  utf-8) e de `.pdf` via **pypdf**; arquivo sem texto extraível vira
  `[]` (chunks vazios).
- AC-003 — [U-002] `TextChunker` divide texto em chunks de `chunk_size`
  caracteres com `overlap`; default `chunk_size=1000`, `overlap=200`.
- AC-004 — [U-003] Tabela `file_chunks` (pgvector) com colunas `id` (PK int),
  `file_id` (FK), `chunk_index`, `content` (text), `embedding` (vector(1024));
  repositório `VectorRepository` (Protocol + SQLAlchemy pgvector) com
  `insert_chunks(file_id, chunks)` e `get_chunks(file_id)`.
- AC-005 — [U-004] Model `File` ganha `chunk_ids: list[int]` (JSONB) e
  `vector_reference: str | None` (UUID do documento no banco vetorial);
  `FileService.create_file` popula esses campos após vetorizar.
- AC-006 — [U-005] Upload síncrono: `POST /chats/{chat_id}/files` extrai texto,
  chunk, embed e persiste vetores **antes** de retornar `FileRead`
  (com `chunk_ids` e `vector_reference` no schema).
- AC-007 — [U-006] Migration Alembic: `CREATE EXTENSION IF NOT EXISTS vector`,
  tabela `file_chunks` com `embedding vector(1024)` e colunas novas em `files`;
  `alembic upgrade head --sql` (offline) emite os comandos.
- AC-008 — [U-001/U-005] Testes (SQLite + fake embedder): service vetoriza e
  popula `chunk_ids`/`vector_reference`; API retorna os ids; extractor de PDF
  com fixture simples.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Banco de vetores: pgvector no postgres existente do compose (F-009). — confirmada
- A-002 — Embedder real: Cohere `cohere/embed-v4.0` (1024 dims) via endpoint
  OpenAI-compatível `https://spillway.ensinoeinstein.com/openai/v1`. — confirmada
- A-009 — Configuração via `.env` (`OPENAI_API_KEY`, `OPENAI_BASE_URL`,
  `OPENAI_MODEL`); `.env` não versionado (gitignored). — confirmada
- A-003 — Nos testes, embedder fake determinístico (sem rede/chave). — confirmada
- A-004 — Extração de texto: texto puro + PDF via pypdf. — confirmada
- A-005 — Chunking por tamanho de caracteres com overlap; default 1000/200. — confirmada
- A-006 — Vetorização síncrona dentro do `POST /chats/{chat_id}/files`. — confirmada
- A-007 — `File` guarda `chunk_ids` (JSONB) + `vector_reference` (UUID). — confirmada
- A-008 — pypdf adicionado como dependência; embedder OpenAI usa a lib
  oficial `openai` (nova dependência). — confirmada

## Perguntas em aberto
- (nenhuma)