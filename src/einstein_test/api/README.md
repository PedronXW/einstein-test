# api — controllers HTTP (camada de apresentação)

Camada **HTTP/FastAPI**: recebe requests e devolve responses. Não contém regra
de negócio nem fala direto com repositórios — apenas injeta serviços (DI) e
traduz entre HTTP e `schemas`.

## Arquivos

- `router.py` — monta e expõe o `FastAPI` com todos os sub-routers (health, auth,
  chats, messages, files).
- `auth.py` / `auth_router.py` — login (emite JWT) e dependências de auth.
- `chats.py`, `files.py`, `messages.py` — endpoints de cada recurso.
- `dependencies.py` — session factory / repositories (somente para injetar no service).

## Fluxo

```
HTTP → router → controller (valida schema) → service (negócio) → response
```

## Fronteiras (regra de ouro F-031)

- **Pode**: importar `services`, `schemas`, config.
- **Não pode**: chamar método de repository/model diretamente, nem definir
  regra de negócio. Garantido por `tests/api/test_layering_rule.py`.
