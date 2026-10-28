# F-034 — Validação de RAG/upload + avisos SSE

## O que foi feito
Revisão das validações do fluxo de mensagens RAG e upload de arquivos.

### Mensagens RAG com avisos SSE (U-001/U-002)
- **Chat sem arquivos `ready`** (`POST /messages`): a mensagem do usuário é
  salva e o stream emite `event: notice` com `{code: "no_ready_files",
  message: ...}` — o LLM **não** é chamado e nenhuma mensagem `assistant` é
  criada (antes: contexto `(vazio)` + resposta alucinada persistida).
- **Chat com `ready` + `pending`/`error`**: o RAG responde normalmente usando
  os arquivos prontos e emite um `event: notice` extra com
  `{code: "partial_files", processing, failed}` informando a cobertura.
- **Fluxo todo `ready`**: nenhum notice (stream normal).
- A decisão de negócio (pode responder? qual aviso?) fica no **service**
  (`FileService.rag_readiness`) — o controller só consome e traduz em SSE
  (layering F-031).
- Contam as mensagens do histórico como antes; o status HTTP continua 200
  (aviso não é erro).

### Validações de upload no service (U-003)
- **Arquivo vazio (0 bytes)** → `EmptyFileError` → **422** (single) /
  `failures[reason="arquivo vazio"]` (batch).
- **Extensão não permitida** → `UnsupportedFileTypeError` → **415** (single) /
  failure `"tipo de arquivo não suportado"` (batch). Whitelist
  `SUPPORTED_EXTENSIONS = {".pdf"} | TEXT_EXTENSIONS` em `services/file.py`
  (fonte única alinhada ao `TextExtractor`).
- **Nome duplicado (case-insensitive)** no mesmo chat com file não deletado →
  `DuplicateFileError` → **409** (single) / failure `"arquivo duplicado"` (batch).
- Regras no **service** (`_validate_upload`), controllers apenas traduzem
  (aderente ao layering do F-031).

### Pergunta em branco (U-004)
- `MessageCreate.content` valida `strip()` não-vazio → **422**.

### Exclusão
- Comportamento atual **mantido** (soft delete sem cascade): documentado como
  limitação conhecida — files/messages órfãos após `DELETE /chats` e vetores/
  objetos do MinIO não limpos em cadeia (ASSUNÇÃO A-004, fora do escopo).

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001 — sem arquivos `ready`: 200 + `event: notice` (`no_ready_files`), sem LLM, sem assistant | PASS | `tests/api/test_message_notices.py -k ac001` |
| AC-002 | U-002 — `ready`+`pending`/`error`: stream normal + notice extra com contagens | PASS | `tests/api/test_message_notices.py -k ac002` |
| AC-003 | U-004 — pergunta em branco → 422 | PASS | `tests/api/test_message_notices.py -k ac003` |
| AC-004 | U-003 — arquivo vazio → 422 (single) / failure (batch) | PASS | `tests/{services,api}/test_*validations*.py -k ac004` |
| AC-005 | U-003 — extensão fora da whitelist → 415 (single) / failure (batch) | PASS | `tests/{services,api}/test_*validations*.py -k ac005` |
| AC-006 | U-003 — nome duplicado → 409 (single) / failure (batch) | PASS | `tests/{services,api}/test_*validations*.py -k ac006` |

## Veredito mecânico
`specs proof --strict F-034-file-message-validation` → `PASS` (6/6 ACs).
`uv run pytest -m "not integration"` → `420 passed, 1 deselected`.
`ruff check .` → all passed.

## Deep review (F4)
6 subagentes `review-*` sobre o diff; achados corrigidos:
- **Layering** (major, quality): a decisão "sem arquivos `ready` ⇒ não chamar
  LLM / não criar assistant" estava no controller → movida para
  `FileService.rag_readiness` (value object); o controller apenas consome.
- **Vocabulário de status** (minor): literais `"pending"/"error"` nos notices →
  usados via `RagReadiness` (constantes no service).
- **Código morto** (minor): lista `notices` inútil removida; `_notice` não é
  mais `async`.
- **Observabilidade** (minor): notice `partial_files` agora logado
  (`event: partial_files_notice`).
- **Segurança** (minor): erros 409/415 não ecoam nome/sufixo do cliente
  (mensagem fixa — evita XSS refletido em frontend que renderize `detail`).
- **Testes** (minor): contagens no AC-002, caso "todo ready sem notice",
  extensão maiúscula aceita, remoção de monkeypatch no-op.
- **Docs/Insomnia** (major, compat): descrições do contrato atualizadas
  (notice SSE, ausência de `[DONE]` sem arquivos, validações 415/409/422 e
  reasons no batch).

## Exemplo de contrato SSE (chat sem arquivos prontos)
```
event: notice
data: {"code":"no_ready_files","message":"nenhum arquivo pronto para responder — envie arquivos"}
```

## Arquivos
- `src/einstein_test/services/file.py` — `_validate_upload`, exceções
  (`EmptyFileError`, `UnsupportedFileTypeError`, `DuplicateFileError`),
  `SUPPORTED_EXTENSIONS`, `rag_readiness`/`RagReadiness` (decisão de negócio).
- `src/einstein_test/api/files.py` — tradução 422/415/409 (single).
- `src/einstein_test/api/messages.py` — consome `rag_readiness` + `event: notice`
  (`no_ready_files`/`partial_files`).
- `src/einstein_test/schemas/message.py` — validator de conteúdo em branco.
- `src/einstein_test/vector/__init__.py` — exporta `TEXT_EXTENSIONS`.
- `docs/insomnia/einstein-test-api.json` — contrato atualizado (SSE + upload).
- `tests/services/test_file_upload_validations.py`, `tests/api/test_upload_validations_api.py`,
  `tests/api/test_message_notices.py` (novos); `tests/conftest.py`
  (`seed_ready_file`); testes existentes adaptados aos novos contratos.