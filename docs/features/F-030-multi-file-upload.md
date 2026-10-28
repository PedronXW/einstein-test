# F-030 — Upload múltiplo de arquivos em uma única chamada

## O que foi feito
Novo endpoint `POST /chats/{chat_id}/files/batch` que recebe vários arquivos
de uma vez (`files: list[UploadFile]`), cria os válidos e reporta os inválidos
na mesma resposta — sem quebrar o upload único existente.

- **Novo endpoint `/batch`**: aceita múltiplos `UploadFile` no campo `files`.
  Responde HTTP **207 Multi-Status** com corpo `{created: FileRead[], failures: []}`
  em toda chamada — `failures` fica vazio quando tudo tem sucesso.
- **Falha parcial, não atômica**: arquivo válido é criado mesmo quando outros
  do lote são inválidos; cada inválido vai para `failures` como
  `{index, name, reason}` (ex.: `arquivo muito grande`). Uma exceção ao
  processar um arquivo individual também vira failure (`falha ao processar arquivo`)
  sem derrubar o restante do lote.
- **Lógica no serviço**: a orquestração do lote (validação de tamanho,
  sanitização de nome, criação por arquivo, coleta de failures) fica em
  `FileService.create_files_batch` — o controller só lê os `UploadFile`, chama
  o serviço e enfileira a vetorização.
- **Limite por lote**: `MAX_FILES_PER_BATCH = 20`; acima disso → **413**.
- **Limite por arquivo preservado**: `MAX_UPLOAD_SIZE = 50MB` por arquivo;
  excedente entra em `failures` sem derrubar o lote.
- **Vetorização em background**: enfileirada para **cada** arquivo criado
  (mesmo fluxo do upload único).
- **404** para chat inexistente, consistente com o upload único.

## Critérios de aceite implementados

| AC | História | Status | Prova |
|----|----------|--------|-------|
| AC-001 | U-001/U-003 — endpoint `/batch` + upload único intacto | PASS | `tests/api/test_multi_file_upload.py -k ac001` |
| AC-002 | U-001 — lote todo válido → 207, created=FileRead[], failures vazio, vetorização por arquivo | PASS | `tests/api/test_multi_file_upload.py -k ac002` |
| AC-003 | U-002 — falha parcial → created só válidos + failures `{index,name,reason}` | PASS | `tests/api/test_multi_file_upload.py -k ac003` |
| AC-004 | U-002 — arquivo >50MB entra em failures sem derrubar o lote | PASS | `tests/api/test_multi_file_upload.py -k ac004` |
| AC-005 | U-001 — >20 arquivos → 413 (MAX_FILES=20) | PASS | `tests/api/test_multi_file_upload.py -k ac005` |
| AC-006 | U-001 — chat inexistente → 404 | PASS | `tests/api/test_multi_file_upload.py -k ac006` |

## Veredito mecânico
`specs proof --strict F-030-multi-file-upload` → `PASS` (6/6 ACs).
`uv run pytest` → `338 passed, 1 deselected`. `ruff check` → all passed.

## Como usar
```bash
curl -X POST http://localhost:8000/chats/1/files/batch \
  -H "Authorization: Bearer <token>" \
  -F "files=@doc1.pdf" \
  -F "files=@relatorio.txt"
```
Resposta (207):
```json
{
  "created": [{"name": "doc1.pdf", "status": "pending", "...": "FileRead"}],
  "failures": [{"index": 1, "name": "relatorio.txt", "reason": "arquivo muito grande"}]
}
```

## Arquivos
- `src/einstein_test/services/file.py` (`FileService.create_files_batch`,
  `BatchFileInput`, `FileUploadFailure`, `FileBatchUploadResult`, `MAX_UPLOAD_SIZE`)
- `src/einstein_test/api/files.py` (endpoint `POST /chats/{chat_id}/files/batch`)
- `src/einstein_test/schemas/file.py` (`FileBatchResult`, `FileBatchFailure`)
- `tests/api/test_multi_file_upload.py` (novo)
- `tests/services/test_file_service.py` (testes do serviço de lote)
