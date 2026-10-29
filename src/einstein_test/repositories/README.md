# repositories — acesso a dados (camada de persistência)

Isolam o SQLAlchemy do resto da aplicação: expõem operações por entidade
(CRUD + buscas). Os controllers **não** os usam diretamente (regra F-031).

## Arquivos

- `sqlalchemy.py` — agrega as implementações `...RepositorySQLAlchemy`.
- `chat.py`, `file.py`, `message.py`, `user.py` — um repositório por entidade.

## Fluxo

```
service → repository (métodos de domínio) → models (SQLAlchemy)
```

## Fronteiras

- **Pode**: importar `models`.
- **Não pode**: importar `api` ou `services`; não definir regra de negócio
  (só acesso a dados).
