# F-018 — Transações atômicas (unit of work)

## O que foi feito
Os repositórios deixaram de executar `commit()` internamente — agora usam
**`flush()`**. A sessão criada por request (`get_session`) é o **Unit of Work**:
commita **uma única vez** ao final do request (bloco `else` do generator) e faz
**rollback** se a operação lançou exceção. Com isso, operações multi-etapa
(`create_file`: File + chunks + chunk_ids; `create_message`: user + assistant)
são **atômicas** — uma falha no meio não deixa registros órfãos. A task Celery
de vetorização também fica atômica (insert dos chunks + update de status num
único commit).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — repositórios usam `flush()` (não commit interno) | PASS | `tests/infra/test_uow.py -k ac001` |
| AC-002 | U-002 — `get_session` commita no fim do request e faz rollback em erro | PASS | `tests/infra/test_uow.py -k ac002` |
| AC-003 | U-002 — `create_message` com falha → rollback sem linhas órfãs | PASS | `tests/infra/test_uow.py -k ac003` |
| AC-004 | U-003 — task Celery atômica (chunks + status num commit; rollback remove chunks) | PASS | `tests/infra/test_uow.py -k ac004` |
| AC-005 | U-001 — suíte completa verde (257 testes) sem regressão | PASS | `tests/infra/test_uow.py` |

## Veredito mecânico
`specs proof --strict F-018-unit-of-work` → `PASS` (5/5 ACs). `uv run pytest` →
`257 passed`.

## Mudanças
- `repositories/{chat,file,message,user}.py` e `vector/repository.py`:
  `session.commit()` → `session.flush()`.
- `api/dependencies.py::get_session`: commit no fim (UoW), rollback em erro,
  close no finally.
- `tests/vector/test_search_similar.py`: `_setup` commita ao final (a sessão
  antes dependia do commit implícito do repositório).

## Arquivos
- `src/einstein_test/repositories/*.py`, `src/einstein_test/vector/repository.py`
- `src/einstein_test/api/dependencies.py` (`get_session` UoW)
- `tests/infra/test_uow.py` (novo), `tests/vector/test_search_similar.py` (ajuste)

## Notas
- O `flush()` garante os ids gerados sem persistir; o commit único do request
  torna o fluxo atômico.
- A task Celery já commitava uma vez ao final — agora com `insert_chunks` por
  flush, chunks+status estão na mesma transação.