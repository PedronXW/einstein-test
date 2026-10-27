# F-012 — Autenticação JWT + isolamento por usuário

## Resumo
A aplicação passa a ter **usuários** e **autenticação JWT**. `POST /users`
registra (email + senha com hash bcrypt), `POST /auth/login` devolve um
`access_token` (JWT). Todos os endpoints de chats, files e messages passam a
exigir `Authorization: Bearer <token>` e **ownership estrito**: cada chat tem
um `user_id` (dono); o usuário só acessa os próprios chats e o conteúdo deles
(files/messages isolados via `chat.user_id`). Arquivos e mensagens **herdam o
isolamento do chat** (sem coluna nova além de `chats.user_id`).

## Histórias de usuário
- U-001 — **Como** usuário, **quero** me registrar em `POST /users`
  (email + senha) e fazer login em `POST /auth/login` para receber um JWT,
  **para** autenticar as próximas requisições.
- U-002 — **Como** usuário autenticado, **quero** que meus chats sejam isolados
  (criados com `user_id` = dono), listados/consultados apenas por mim,
  **para** que ninguém acesse meus dados.
- U-003 — **Como** dev, **quero** um dependency `get_current_user`
  (`Authorization: Bearer`) reutilizável nos routers, **para** proteger
  endpoints sem duplicação.
- U-004 — **Como** dev, **quero** que files e messages validem ownership via
  `chat.user_id`, **para** não expor conteúdo de chats alheios.
- U-005 — **Como** dev, **quero** que os testes usem um fixture de usuário
  autenticado (token fake) sem depender de rede, **para** validar isolamento.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-001] Model `User` (`id`, `email` único, `password_hash`,
  timestamp mixin) + migration; `RepositoryUser` (Protocol + SQLAlchemy) com
  `create`, `create_by_email`. Dependências `bcrypt` e `pyjwt`.
- AC-002 — [U-001] `POST /users` registra usuário (senha hasheada com bcrypt;
  email validado/único; erro 409 se existir). `POST /auth/login` valida
  credenciais e retorna `{"access_token": "<jwt>", "token_type": "bearer"}`.
- AC-003 — [U-003] Dependências `get_current_user` (lê `Authorization: Bearer`,
  decodifica JWT, carrega User do banco; falha → 401) e função `create_access_token`.
  Config via env `JWT_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60).
- AC-004 — [U-002] `Chat.user_id` (FK users) + migration; `ChatService.create`
  exige `user_id`; `ChatRepository.list(user_id)` e `get_by_id` filtram por dono;
  chats alheios → 404.
- AC-005 — [U-002/U-004] Routers de **chats**: `POST /chats`, `GET /chats`,
  `GET /chats/{id}`, `DELETE /chats/{id}` exigem `get_current_user`; list/get
  só do dono. Status existente preservado (404 para alheio — não vaza existência).
- AC-006 — [U-004] Routers de **files** e **messages**: exigem
  `get_current_user`; antes de qualquer operação, o chat é verificado como do
  dono (`_ensure_chat_owned`) → 404 se não for.
- AC-007 — [U-005] Testes de API: fixture autenticado (token fake/JWT assinado
  no teste); cenários: registro, login, chat isolado entre dois usuários,
  files/messages de chat alheio → 404. Testes existentes adaptados com o
  fixture autenticado.
- AC-008 — [U-001] Login inválido → 401 (`senha inválida`/`usuário não existe`
  sem detalhar qual); rota inexistente de auth preservada.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Registro público (`POST /users`) + login (`POST /auth/login`) JWT. — confirmada
- A-002 — Ownership estrito: list/get/delete só do dono; chats alheios → 404. — confirmada
- A-003 — Hash de senha com bcrypt. — confirmada
- A-004 — Files/messages herdam isolamento via `chat.user_id`. — confirmada
- A-005 — `get_current_user`/`create_access_token` como dependências reutilizáveis. — confirmada
- A-006 — JWT com `pyjwt` + `bcrypt` (deps novas). — confirmada

## Perguntas em aberto
- (nenhuma)