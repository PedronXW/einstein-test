# F-031 — Refactor layering controller-service-repository-model

## Resumo
Auditoria completa do layering revelou violações da regra de ouro
`controller(api) -> service -> repository -> model`. Esta feature corrige todas
(crítico + major + minor), sem mudança de comportamento externo — é refactor
estrutural com a mesma API HTTP, mesmos dados e mesmos contratos.

Eixos da correção:
- **Auth/User**: controller para de chamar repository direto (novo `UserService`),
  regra de negócio de modelo (allowlist/default) sai dos controllers, bcrypt sai
  do repository (módulo `security`), `DEFAULT_USER_MODEL` sai do model.
- **File/Tasks**: orquestração de vetorização vira método público de service
  (`FileService.vectorize_uploaded`), task fica fina; engine factory sai de
  `api/dependencies` para `db/engine.py` (task não depende mais de `api`);
  limites de domínio (`MAX_UPLOAD_SIZE`, `MAX_FILES_PER_BATCH`) validados no
  service; `FILE_STATUS_*` sai do model; uuid de `vector_reference` com fonte
  única.
- **Vector/RAG**: defaults de ranking saem do repository (quem chama passa
  explicitamente); constante única em `services/rag/graph.py`.
- **Minor**: parsing `s3://` unificado em `storage`, `repositories/__init__`
  deixa de re-exportar de `vector/`, `AuthService.with_session` removido.

## Histórias de usuário
- U-001 — **Como** dev, **quero** que controllers falem apenas com services,
  **para** manter as camadas isoladas e a regra controller→service→repo→model
  em todo o sistema.
- U-002 — **Como** dev, **quero** que regras de negócio (limites, status,
  modelo padrão, orquestração) vivam no service, **para** que chamadores não-HTTP
  (tasks, testes) respeitem as mesmas regras do endpoint.
- U-003 — **Como** dev, **quero** remover dependências invertidas
  (`tasks→api`, service→repo concreto via `with_session`), **para** evitar
  acoplamento e ciclos de import.
- U-004 — **Como** dev, **quero** que vocabulário de domínio e segurança
  (status de file, modelo default, hash bcrypt) fiquem fora de model/repository,
  **para** separar persistência de negócio.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] Controller de auth deixa de chamar repository/model direto:
  `get_current_user` usa `UserService.get_by_email`; `update_me` e o fallback de
  modelo em messages usam `UserService.set_model`/`resolve_model` (allowlist +
  default aplicados no service).
- AC-002 — [U-004] `hash_password`/`verify_password` saem de `repositories/user`
  para módulo `security`; `UserRepositorySQLAlchemy.create` persiste o hash
  pronto (não sabe que bcrypt existe); `AuthService` orquestra hash/verify.
- AC-003 — [U-004] `DEFAULT_USER_MODEL` e `FILE_STATUS_*` deixam de morar em
  model; passam a ser expostos por `services/user.py` e `services/file.py`
  (model mantém apenas default literal da coluna).
- AC-004 — [U-002] `FileService.create_file` valida `MAX_UPLOAD_SIZE` (lança
  `FileTooLargeError`); `create_files_batch` valida `MAX_FILES_PER_BATCH`
  (lança exceção de domínio); controllers apenas traduzem para HTTP 413.
- AC-005 — [U-002] `FileService.vectorize_uploaded(file_id)` orquestra
  vetorização (carrega repo, baixa storage, `_vectorize`, transições de status
  via repo, commit); a task Celery fica fina e `_mark_error` usa o service/repo.
- AC-006 — [U-003] `create_engine_from_config` move para `db/engine.py`;
  `api/dependencies` reutiliza de lá; task importa de `db`, nunca de `api`.
- AC-007 — [U-002] `VectorRepository.search_similar` deixa de ter defaults de
  domínio (`chunks_per_file`/`max_chunks` obrigatórios); `services/rag/graph.py`
  é a fonte única da política (`CHUNKS_PER_FILE=2`, `MAX_CHUNKS=12`).
- AC-008 — [U-001/U-003] Minor: `repositories/__init__` não re-exporta de
  `vector/`; `repositories/sqlalchemy.py` inclui `UserRepositorySQLAlchemy`;
  parsing `s3://` unificado em `storage`; `AuthService.with_session` removido.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Soft-delete (`deleted_at`) permanece decidido no repository como
  convenção de persistência (storage strategy), não regra de negócio — confirmada.
- A-002 — Ranking top-K (window function ROW_NUMBER por file_id) permanece no
  repository como consulta de persistência; apenas os DEFAULTS de domínio saem
  dele (quem chama passa explicitamente) — confirmada.
- A-003 — `get_current_user` continua retornando o model `User` (contrato da
  dependência de auth), mas o acesso a dados passa por `UserService` — confirmada.
- A-004 — Mudança 100% estrutural: nenhum contrato HTTP/dados muda (mesmos
  endpoints, status, schemas e colunas) — confirmada.

## Perguntas em aberto
- Q-001 — Escopo da correção? → `Tudo (C+M+minor)` (resolvida).
- Q-002 — Estratégia de specs? → `1 spec única` (resolvida).
- Q-003 — Onde colocar `get_current_user`? → `UserService novo` (resolvida).
- Q-004 — Soft-delete? → `Manter no repo` (resolvida).
- Q-005 — Ranking top-K? → `Só tira defaults do repo` (resolvida).
