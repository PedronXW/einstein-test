"""Segurança: hash/verify de senha (bcrypt).

Política criptográfica isolada da persistência — o repository persiste o hash
já pronto; este módulo é a única fonte de bcrypt.
"""

import bcrypt


def hash_password(password: str) -> str:
    """Hash bcrypt da senha (salteado)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica senha contra o hash bcrypt."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except ValueError:
        return False


__all__ = ["hash_password", "verify_password"]
