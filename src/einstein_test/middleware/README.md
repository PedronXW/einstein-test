# middleware — processamento transversal a todos os requests

Middlewares ASGI aplicados a **todas** as rotas, antes dos controllers.

## Arquivos

- `logging_middleware.py` — access log JSON com `request_id` por request
  (header `X-Request-Id` presente em toda resposta, inclusive 429/500 e SSE).
- `rate_limit.py` — rate limiting por usuário autenticado / IP anônimo
  (F-016/F-029), com backends `memory` (default) e `redis`
  (`RATE_LIMIT_BACKEND=redis`, cai para memória se o Redis cair).

## Ordem (execução)

Em `main.py` o `RequestIdMiddleware` é adicionado por último → é o mais externo
e roda primeiro; depois o rate limit; só então o router.

```
RequestId → rate_limit → router
```
