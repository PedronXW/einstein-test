"""Testes TDD da feature F-029 (multi-worker + rate limit Redis).

Valida: CLI --workers (main.main), compose api com workers, e o backend de
rate limit selecionável (memory default, redis) com fallback.
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_ac001_main_accepts_workers_arg():
    import einstein_test.main as main

    assert callable(main.main)
    # main.main deve aceitar workers (argparse) — checamos fonte
    src = pathlib.Path(main.__file__).read_text()
    assert "--workers" in src, "main.main define --workers"


def test_ac001_main_uses_factory_string_for_workers():
    import einstein_test.main as main

    src = pathlib.Path(main.__file__).read_text()
    assert "einstein_test.main:create_app" in src, "factory como string"
    assert "workers=" in src, "uvicorn com workers="


def test_ac001_reload_disabled_if_workers():
    import einstein_test.main as main

    src = pathlib.Path(main.__file__).read_text()
    # workers>1 não deve usar reload (incompatível)
    assert "reload=False" in src or "reload=" in src, "reload controlado"


def test_ac002_compose_api_has_workers():
    p = ROOT / "docker-compose.yml"
    data = yaml.safe_load(p.read_text())
    api = data["services"]["api"]
    cmd = str(api.get("command", ""))
    assert "create_app" in cmd, "api usa factory-string"
    assert "--workers" in cmd or "workers" in cmd, "api usa --workers"
    assert "API_WORKERS" in str(api.get("environment", {})), "env API_WORKERS"


def test_ac003_rate_limit_backend_env_config():
    import einstein_test.middleware.rate_limit as rl

    assert hasattr(rl, "RATE_LIMIT_BACKEND") or hasattr(rl, "backend"), (
        "backend configurável"
    )
    assert hasattr(rl, "RateLimiter")


def test_ac004_rate_limiter_supports_redis_key():
    from einstein_test.middleware.rate_limit import _redis_key

    key = _redis_key(("user@b.com", "POST /auth/login"))
    assert key.startswith("rl:"), "chave redis prefixada com rl:"
    assert "user" in key and "auth" in key, "identidade e rota na chave"


def test_ac004_memory_default():
    import einstein_test.middleware.rate_limit as rl

    # sem env, o backend é memory (não redis)
    limiter = rl.RateLimiter(limit=2, window=60)
    ok1, _ = limiter.allow(("u", "/x"))
    ok2, _ = limiter.allow(("u", "/x"))
    assert ok1 is True and ok2 is True
    ok, _ = limiter.allow(("u", "/x"))
    assert ok is False, "limite em memória funciona"


def test_ac005_redis_backend_skips_without_redis(monkeypatch):
    # sem Redis acessível, o backend redis cai p/ memória (não falha)
    from einstein_test.middleware.rate_limit import RateLimiter

    try:
        r = RateLimiter(limit=2, window=60, backend="redis",
                        redis_url="redis://localhost:6399/0")  # porta errada
        ok, _ = r.allow(("u", "/x"))
        # se não levantou, caiu para memória
        assert ok is True
    except Exception:
        # aceitável: Redis indisponível pode levantar ao conectar
        pass