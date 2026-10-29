# F-038 — Harness de avaliação do RAG (assertividade e características de IA)

## O que foi feito
Uma ferramenta para **validar o RAG** por evidência, medindo:
- **Retrieval**: `recall@k` (k=5,12), `MRR@5`, `hit@1` por pergunta — se o
  contexto certo é recuperado;
- **Assertividade da resposta**: `correctness`, `faithfulness` (groundedness,
  sem alucinação) e `coverage` via **LLM-as-judge** (rubric 1–5), com
  `FakeJudge` determinístico para o CI;
- **Similaridade semântica** (cosseno answer × gold);
- **Robustez**: pergunta fora do corpus → não deve fabricar resposta;
- **Perf**: TTFT e latência total por pergunta.

### Dataset gold híbrido (`eval/`)
- `eval/corpus/` — documentos: `aurora-lms.md` (sintético, fatos exatos),
  `equipe.md` (sintético) e `aprendizagem-ativa.md` (natural).
- `eval/dataset/dev.jsonl` — 6 perguntas: 4 sintéticas (gold objetiva), 1
  natural (síntese) e 1 `edge=no_context` (fora do corpus).
- **Isolamento**: 1 chat por pergunta, ingerindo só os arquivos de
  `expected_files` — ground-truth de retrieval limpo.

### Módulo `src/einstein_test/eval/`
| Arquivo | Papel |
|---|---|
| `metrics.py` | `recall_at_k`, `mrr_at_k`, `hit_rate_at_1` (puras) |
| `dataset.py` | `EvalQuestion` + carregador JSONL + corpus |
| `judge.py` | `Judge` Protocol, `FakeJudge`, `LLMJudge` (`EVAL_JUDGE_MODEL`) |
| `generation.py` | `run_generation` via `rag_service.astream` + contexto + TTFT/latência |
| `runner.py` | `run_eval` agrega métricas + veredito + similaridade + robustez |
| `report.py` | render Markdown/HTML/JSON |
| `cli.py` / `__main__.py` | CLI `python -m einstein_test.eval` |

### CLI
```bash
# Smoke determinístico (fakes, sem chave) — CI
uv run python -m einstein_test.eval --backend fake --limit 2

# Avaliação real (requer OPENAI_API_KEY + infra) — opt-in
uv run python -m einstein_test.eval --backend real --judge llm \
    --format html --out eval/reports/latest.html
```
`--backend fake` usa um *retriever/juiz* "perfeitos" (recall e correctness
altos), validando a **mecânica** do harness; `--backend real` ingere o corpus
num chat, vetoriza de verdade e roda o RAG.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-002 — métricas de retrieval puras (recall@k, MRR@k, hit@1) | PASS | `tests/eval/test_metrics.py` |
| AC-002 | U-003 — Judge Protocol + FakeJudge + LLMJudge (veredito 1–5) | PASS | `tests/eval/test_judge.py` |
| AC-003 | U-001 — geração coleta resposta + contexto + TTFT/latência (via `rag_service.astream`) | PASS | `tests/eval/test_generation.py` |
| AC-004 | U-004 — CLI + relatório (Markdown/HTML/JSON) | PASS | `tests/eval/test_report_and_cli.py` |
| AC-005 | U-005 — smoke determinístico (fakes) roda no CI | PASS | `tests/eval/` (suíte) |
| AC-006 | U-006 — similaridade semântica + robustez (no_context não fabrica) | PASS | `tests/eval/test_runner.py` |

## Veredito mecânico
`specs proof F-038-rag-eval` → `PASS` (6/6 ACs).
`uv run pytest -m "not integration"` → `475 passed, 1 deselected`.
`uv run ruff check .` → all passed.
CLI fake (dataset real) → agregados: recall@5=1.000, correctness=5.000,
robustez=0.833 (q6 `no_context` corretamente flagrada).

## Notas e custos
- **Smoke no CI = grátis** (fakes, zero tokens). O eval real (LLM-judge +
  embeddings + RAG) consome tokens do provedor — usar `EVAL_JUDGE_MODEL` e
  `--limit` para controlar.
- Juiz usa `EVAL_JUDGE_MODEL` (default `azure/gpt-6-luna`), mesmo provedor do
  RAG. `--judge fake` também disponível no backend real (sem custo).
- `--backend real` **vetoriza de verdade** (o `FileService` recebe o
  `vector_repository`; `create_file` extrai/chunka/embed na ingestão) e, ao
  fim, **limpa** as linhas criadas (chunks/files/chats/user). Roda apenas
  contra **banco local** (`localhost`/`127.0.0.1`/`sqlite`) a menos que
  `EVAL_ALLOW_NON_LOCAL=1`; objetos órfãos do storage podem permanecer.
- Dataset é **expansível**: basta adicionar documentos ao corpus e linhas ao
  JSONL (cada pergunta com `expected_files` e `gold_answer`). Nomes de corpus
  são validados contra path traversal.

## Arquivos
- `src/einstein_test/eval/` (novo pacote: `__init__`, `metrics`, `dataset`,
  `judge`, `generation`, `runner`, `report`, `cli`, `__main__`)
- `tests/eval/` (novo: `test_metrics`, `test_dataset`, `test_judge`,
  `test_generation`, `test_runner`, `test_report_and_cli`)
- `eval/corpus/{aurora-lms,equipe,aprendizagem-ativa}.md` (novo)
- `eval/dataset/dev.jsonl` (novo)
- `docs/features/F-038-rag-eval.md` (este)