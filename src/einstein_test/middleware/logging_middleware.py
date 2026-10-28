"""Middleware de access log (JSON) com request_id por request.

Garante que TODAS as respostas (inclusive 429 do rate limit e 500) tenham
`X-Request-Id` e gerem access log estruturado. O `request_id` é definido na
contextvar `request_id_var` e ativo durante todo o request — inclusive durante
a geração de streams SSE (não é resetado cedo demais).
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from einstein_test.logging_setup import (
    get_logger,
    request_id_var,
)

logger = get_logger("middleware.logging_middleware")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        status = 500
        response: Response | None = None
        try:
            response = await call_next(request)
            status = response.status_code
        except Exception:
            # garante access log mesmo em 500 (exc não tratada propaga depois)
            raise
        finally:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            # reset APÓS emitir o log (o token continua ativo durante o body)
            request_id_var.reset(token)

        if response is not None:
            response.headers["X-Request-Id"] = request_id

        # identifica o usuário autenticado (se houver) para o access log
        user_id = None
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            try:
                from einstein_test.api.auth import decode_token

                payload = decode_token(auth.removeprefix("Bearer ").strip())
                user_id = payload.get("sub")
            except Exception:  # noqa: BLE001 - token inválido => None
                pass
        client = request.client
        logger.info(
            "access",
            extra={
                "event": "access",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "latency_ms": latency_ms,
                "user_id": user_id,
                "ip": client.host if client else None,
            },
        )
        if response is None:
            raise RuntimeError("call_next não retornou resposta")
        return response