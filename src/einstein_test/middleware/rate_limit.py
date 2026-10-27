"""Middleware de rate limiting (F-016).

Limitador por usuário (autenticado) ou IP (anônimo), contado em memória com
janela deslizante. Responde 429 + Retry-After quando excedido. Limites por
rota configuráveis via env; rotas abertas (docs/health) excluídas.

Nota de segurança: `X-Forwarded-For` só deve ser confiado quando o cliente
direto é um proxy confiável (env `TRUSTED_PROXIES`); caso contrário, usa
`request.client.host` — impedindo spoofing que burlaria limites por IP.
"""

import os
import threading
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from einstein_test.api.auth import decode_token

# Rotas excluídas do rate limiting (infra/docs).
EXCLUDED_PATHS = ("/docs", "/redoc", "/openapi.json", "/health")

# Limites default (req/min por rota).
DEFAULT_LIMITS = {
    "POST /auth/login": 10,
    "POST /chats": 30,
    "POST /chats/{id}/messages": 20,
    "POST /chats/{id}/files": 10,
    "POST /users": 20,
}
DEFAULT_GLOBAL_LIMIT = 120
MAX_KEYS = 10_000


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


def _route_limits() -> dict[str, int]:
    """Monta os limites por rota com override por env (RATE_LIMIT_*)."""
    return {
        "POST /auth/login": _env_int("RATE_LIMIT_LOGIN", DEFAULT_LIMITS["POST /auth/login"]),
        "POST /chats": _env_int("RATE_LIMIT_CHATS", DEFAULT_LIMITS["POST /chats"]),
        "POST /chats/{id}/messages": _env_int(
            "RATE_LIMIT_MESSAGES", DEFAULT_LIMITS["POST /chats/{id}/messages"]
        ),
        "POST /chats/{id}/files": _env_int(
            "RATE_LIMIT_FILES", DEFAULT_LIMITS["POST /chats/{id}/files"]
        ),
        "POST /users": _env_int("RATE_LIMIT_USERS", DEFAULT_LIMITS["POST /users"]),
    }


def _route_for(path: str) -> str | None:
    """Normaliza o path para o limite de rota (ex.: /chats/1/messages)."""
    if path == "/auth/login":
        return "POST /auth/login"
    if path == "/users":
        return "POST /users"
    if path == "/chats":
        return "POST /chats"
    parts = path.strip("/").split("/")
    if len(parts) >= 2 and parts[0] == "chats":
        if len(parts) == 2 and parts[1].isdigit():
            return None  # POST /chats/{id} (chat único) — só global
        if len(parts) == 3 and parts[2] == "messages":
            return "POST /chats/{id}/messages"
        if len(parts) == 3 and parts[2] == "files":
            return "POST /chats/{id}/files"
    return None


class RateLimiter:
    """Janela deslizante em memória, chave = (identidade, rota)."""

    _lock = threading.Lock()
    _entries: dict[tuple[str, str], list[float]] = defaultdict(list)

    def __init__(self, limit: int, window: int = 60) -> None:
        self.limit = limit
        self.window = window

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._entries = defaultdict(list)

    def allow(self, key: tuple[str, str]) -> tuple[bool, int | None]:
        """Retorna (permitido, retry_after_seconds). Atômico por lock."""
        now = time.time()
        with self._lock:
            if len(self._entries) >= MAX_KEYS and key not in self._entries:
                # evita memory-DoS por chaves ilimitadas
                return True, None
            history = [t for t in self._entries[key] if now - t < self.window]
            self._entries[key] = history
            if len(history) >= self.limit:
                oldest = self._entries[key][0]
                retry = int(self.window - (now - oldest)) + 1
                return False, max(retry, 1)
            self._entries[key].append(now)
            return True, None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Aplica limites por usuário/IP às rotas sensíveis."""

    def __init__(self, app, *, window: int = 60) -> None:
        super().__init__(app)
        self.window = window
        self.global_limit = _env_int("RATE_LIMIT_GLOBAL", DEFAULT_GLOBAL_LIMIT)
        self.limiter = RateLimiter(self.global_limit, window=self.window)
        self.trusted_proxies = {
            p.strip()
            for p in os.getenv("TRUSTED_PROXIES", "").split(",")
            if p.strip()
        }

    def _identity(self, request: Request) -> str:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            try:
                payload = decode_token(auth.removeprefix("Bearer ").strip())
                sub = payload.get("sub")
                if sub:
                    return f"user:{sub}"
            except Exception:  # noqa: BLE001 - token inválido cai para IP
                pass
        client = request.client
        peer = client.host if client else "unknown"
        forwarded = request.headers.get("x-forwarded-for")
        # só confia em XFF vindo de um proxy confiável (entrada mais à direita
        # que o proxy acrescenta); caso contrário usa o peer direto.
        if forwarded and peer in self.trusted_proxies:
            parts = [p.strip() for p in forwarded.split(",")]
            return parts[-1] if parts else peer
        return f"ip:{peer}"

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith(EXCLUDED_PATHS):
            return await call_next(request)

        identity = self._identity(request)
        method = request.method
        limits = _route_limits()
        route = _route_for(path) if method == "POST" else None

        # limite específico da rota (POST sensíveis), lido por request (env)
        if route and route in limits:
            route_limiter = RateLimiter(limits[route], window=self.window)
            ok, retry = route_limiter.allow((identity, route))
            if not ok:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "muitas requisições, tente novamente em breve"},
                    headers={"Retry-After": str(retry)},
                )

        # limite global por identidade (chave separada da de rota)
        ok, retry = self.limiter.allow((identity, "global"))
        if not ok:
            return JSONResponse(
                status_code=429,
                content={"detail": "muitas requisições, tente novamente em breve"},
                headers={"Retry-After": str(retry)},
            )

        return await call_next(request)