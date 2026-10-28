# F-024 — Testes de integração opcionais (marker integration)

## Resumo
Cria uma suíte de **testes de integração opcionais** que usa o **provedor real**
(OpenAI-compatível via spillway) para validar o fluxo ponta-a-ponta: upload real
→ vetorização (embeddings reais) → pergunta → SSE streaming (LLM real). Esses
testes ficam **marcados com `@pytest.mark.integration`** e **excluídos do CI
padrão** (adicionados ao `addopts` de desabilitar ou a um perfil `-m
"not integration"`), rodando apenas quando há `OPENAI_API_KEY`/`RUN_INTEGRATION`
e a infra (postgres/minio/redis) está de pé.

## Histórias de usuário
- U-001 — **Como** dev, **quero** uma suíte de integração real (LLM/embedders
  verdadeiros) separada dos testes unitários, **para** validar o fluxo
  end-to-end antes de release.
- U-002 — **Como** dev, **quero** que o CI padrão **não** rode a integração
  (sem chave/infra), **para** não falhar por ausência de credenciais.
- U-003 — **Como** dev, **quero** que a suíte de integração seja **skipada**
  graciosamente quando a chave/endpoint não estiverem configurados, **para**
  não quebrar o `pytest` local.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-002] Marker `integration` registrado em `pyproject.toml`
  (`[tool.pytest.ini_options] markers`); `addopts`/perfil exclui integração no
  CI padrão (`-m "not integration"`), mas a suíte padrão continua verde.
- AC-002 — [U-003] Conftest de integração (`tests/integration/`): fixture
  `integration_available` que skipa se `OPENAI_API_KEY` ausente ou
  `RUN_INTEGRATION != "1"`; testes marcados `@pytest.mark.integration`.
- AC-003 — [U-001] Teste de integração: `test_rag_end_to_end` sobe um app real
  (postgres/minio/redis via compose) e faz upload de um arquivo de exemplo,
  aguarda status `ready`, pergunta e verifica SSE com `[DONE]` e `assistant`
  salva. Skip (não falha) sem infra/chave.
- AC-004 — [U-002] O CI padrão continua rodando **sem** integração (suíte
  principal verde); a integração é ativada explicitamente
  (`RUN_INTEGRATION=1 uv run pytest -m integration`).

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Marker `integration` + exclusão do CI padrão (`-m "not integration"`). — confirmada
- A-002 — Skip gracioso sem chave/infra (não falha o pytest). — confirmada
- A-003 — Teste end-to-end real (upload→ready→pergunta→SSE) em
  `tests/integration/`. — confirmada

## Perguntas em aberto
- (nenhuma)