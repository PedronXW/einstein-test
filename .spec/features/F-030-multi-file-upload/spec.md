# F-030 — Upload múltiplo de arquivos em uma única chamada

## Resumo
Hoje o endpoint `POST /chats/{chat_id}/files` aceita **um** arquivo por chamada
(F-007). Esta feature adiciona um **novo** endpoint `POST /chats/{chat_id}/files/batch`
que recebe vários arquivos de uma vez, cria os válidos e reporta os inválidos
na mesma resposta — sem quebrar o upload único existente.

Decisões de design (confirmadas com o usuário):
- **Novo endpoint `/batch`** — o endpoint de arquivo único permanece intacto
  (sem quebra de compatibilidade).
- **Falha parcial, não atômica** — arquivos válidos são criados mesmo quando
  há inválidos na mesma chamada.
- **Resposta HTTP 207 Multi-Status** com corpo misto `{created, failures}`.
- **Limite de 20 arquivos por chamada** (`MAX_FILES = 20`).

## Histórias de usuário
- U-001 — **Como** usuário, **quero** enviar vários arquivos em uma única
  chamada, **para** carregar um lote de documentos sem N chamadas de ida e
  volta.
- U-002 — **Como** usuário, **quero** saber quais arquivos falharam no lote,
  **para** corrigir apenas os inválidos sem reenviar o lote inteiro.
- U-003 — **Como** usuário, **quero** que o upload único continue funcionando,
  **para** não quebrar meus clientes atuais.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001/U-003] Novo endpoint `POST /chats/{chat_id}/files/batch`
  aceita `files` (múltiplos UploadFile) e retorna 207; o endpoint atual de
  arquivo único continua inteiro e funcional.
- AC-002 — [U-001] Com todos os arquivos válidos: 207 com `created` contendo
  N FileRead (mesmos campos do upload único) e `failures` vazio; vetorização
  enfileirada para cada arquivo criado.
- AC-003 — [U-002] Com falha parcial: `created` tem só os válidos e `failures`
  lista `{index, name, reason}` dos inválidos; os válidos são persistidos mesmo
  com inválidos presentes (não atômico).
- AC-004 — [U-002] Arquivo individual acima de 50MB entra em `failures`
  (reason) sem derrubar o lote; limite de 50MB por arquivo preservado.
- AC-005 — [U-001] Chamada com mais de 20 arquivos → HTTP 413 (`MAX_FILES=20`).
- AC-006 — [U-001] Chat inexistente → HTTP 404, consistente com o upload único.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Novo endpoint `/batch`, sem alterar o de arquivo único, por escolha
  do usuário — confirmada.
- A-002 — Falha parcial não-atômica (cria válidos e reporta inválidos) — confirmada.
- A-003 — Resposta HTTP 207 com corpo misto `{created, failures}` — confirmada.
- A-004 — Limite de 20 arquivos por chamada — confirmada.

## Perguntas em aberto
- Q-001 — Como expor o upload múltiplo? → `Novo endpoint /batch` (resolvida).
- Q-002 — Comportamento se um arquivo falhar? → `Parcial: cria os válidos e reporta erros` (resolvida).
- Q-003 — Formato de resposta? → `207 + corpo misto created/failures` (resolvida).
- Q-004 — Limite de arquivos por chamada? → `Máx. 20` (resolvida).
