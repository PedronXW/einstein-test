# F-038 — Harness de avaliação do RAG (assertividade e características de IA)

## Resumo
Uma suíte/ferramenta para **validar a assertividade do RAG** e outras
características de IA: qualidade do **retrieval** (recall@k, MRR), **assertividade
da resposta** (correção/fidelidade/cobertura via LLM-as-judge), robustez,
perf/custo e consistência. Um **CLI** roda retrieval + geração sobre um
**dataset gold híbrido** (fatos exatos sintéticos + documentos naturais) e gera
relatório (Markdown/HTML/JSON). Um **smoke determinístico** (fakes, sem chave)
valida a mecânica do harness no CI.

## Histórias de usuário
- U-001 — **Como** desenvolvedor, **quero** medir a assertividade das respostas
  do RAG, **para** confiar no sistema antes de liberar.
- U-002 — **Como** desenvolvedor, **quero** métricas de retrieval (recall@k,
  MRR@k, hit-rate@1), **para** medir se o contexto certo é recuperado.
- U-003 — **Como** desenvolvedor, **quero** julgar a resposta (correção,
  fidelidade, cobertura) via juiz de LLM com fake determinístico, **para**
  automatizar a avaliação.
- U-004 — **Como** desenvolvedor, **quero** um CLI que rode a avaliação e gere
  relatório, **para** comparar versões e regressões.
- U-005 — **Como** desenvolvedor, **quero** um smoke determinístico no CI
  (fakes), **para** validar a mecânica do harness sem custo de tokens.
- U-006 — **Como** desenvolvedor, **quero** métricas de robustez, perf e custo
  no run, **para** acompanhar qualidade além da assertividade.

## Critérios de aceite
> Critérios são registrados mecanicamente (AC-### → story → semântica técnica → dono T-###)
> — edite `criteria.reg` e reflita aqui por legibilidade ponto a ponto.

- AC-001 — [U-002] Métricas de retrieval: `recall@k` (k=5,12), `MRR@k`,
  `hit-rate@1` por pergunta, a partir dos `expected_files`; funções puras
  testáveis.
- AC-002 — [U-003] `Judge` Protocol com `FakeJudge` determinístico e
  `LLMJudge`; veredito com `correctness`, `faithfulness`, `coverage` (1–5).
- AC-003 — [U-001/U-006] Runner de geração coleta resposta (via `rag_service.astream`),
  contexto e métricas de perf (TTFT, latência total) e contagem de tokens.
- AC-004 — [U-004] CLI executa retrieval/geração/full e gera relatório
  (Markdown/HTML/JSON).
- AC-005 — [U-005] Smoke determinístico (FakeEmbedder + FakeChatLLM + FakeJudge)
  roda no CI e valida dataset, métricas, geração, juiz e relatório sem chave.
- AC-006 — [U-006] Similaridade semântica (cosine answer × gold) e robustez:
  chat sem arquivos → notice; pergunta fora do corpus → não fabrica fato.

## Suposições (status: aberto|confirmada|rejeitada)
- A-001 — Isolamento por pergunta: 1 chat por pergunta, ingerindo só os docs de
  `expected_files` — confirmada.
- A-002 — Métricas de retrieval em nível de **arquivo** (`expected_files`), não
  de chunk — confirmada.
- A-003 — Juiz de LLM usa modelo configurável `EVAL_JUDGE_MODEL` (default
  `azure/gpt-6-luna`) sobre o mesmo provedor OpenAI-compatível — confirmada.
- A-004 — Smoke no CI usa fakes (zero tokens); eval completo é opt-in com chave
  real e `--limit` para controlar custo — confirmada.
- A-005 — Dataset híbrido inicial pequeno (`eval/dataset/`, ~6 perguntas)
  autorado por nós e expansível — confirmada.

## Perguntas em aberto
- (nenhuma)