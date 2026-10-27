# F-018 — Transações atômicas (unit of work)

## Resumo
Hoje cada repositório executa seu próprio `commit()` — operações multi-etapa
(`create_file`: persistir File + vetorizar + update chunk_ids; `create_message`:
user + assistant) commitam em vários momentos, deixando **estado parcial** se
algo falha no meio. A feature introduz um **Unit of Work**: a sessão é criada
por request, os repositórios fazem **flush** (não commit) e o **commit ocorre
uma única vez** ao final do request (ou na task), com **rollback automático** em
erro. A task Celery de vetorização também ganha atomicidade (insere chunks +
atualiza status num único commit).

## Histórias de usuário
- U-001 — **Como** dev, **quero** que os repositórios não commitem internamente
  (só flushem), **para** que uma operação multi-etapa seja atômica.
- U-002 — **Como** dev, **quero** que o request commite uma única vez ao final
  (com rollback em erro), **para** não deixar registros órfãos.
- U-003 — **Como** dev, **quero** que a task Celery de vetorização seja
  atômica (chunks + status num commit), **para** idempotência e integridade.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] Repositórios (chat/file/message/user/vector) substituem
  `session.commit()` por `session.flush()` nos métodos de escrita
  (`create`/`insert_chunks`/etc.). O `delete` (soft) também usa flush.
- AC-002 — [U-002] `get_session` passa a commitar ao final do request (commit
  no `finally`/após yield) e fazer rollback se a operação lançou; a API não
  precisa commitar manualmente nos services.
- AC-003 — [U-002] Testes: `create_file` com vetorização que falha → rollback
  (nenhum File/FileChunk órfão); `create_message` que falha → nenhuma linha;
  caminho feliz persiste normalmente.
- AC-004 — [U-003] Task Celery `vectorize_file` insere chunks e atualiza
  status/error num **único commit** (rollback total em erro); teste de
  idempotência/atomicidade da task.
- AC-005 — [U-001] Suíte completa continua verde (252+ testes sem quebra de
  comportamento); commit único preservado nos caminhos felizes.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Unit of Work: repos flusheiam, sessão do request commita no final. — confirmada
- A-002 — Rollback automático em erro na sessão do request. — confirmada
- A-003 — Task Celery atômica (chunks + status num commit). — confirmada
- A-004 — Testes de rollback/atomicidade. — confirmada

## Perguntas em aberto
- (nenhuma)