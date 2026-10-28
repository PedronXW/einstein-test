"""Serviço de User — acesso a dados e regra de modelo (allowlist/default)."""

from einstein_test.models.user import User
from einstein_test.repositories import UserRepository
from einstein_test.services.rag import allowed_models

DEFAULT_USER_MODEL = "azure/gpt-5-mini"


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository: UserRepository = repository

    def get_by_email(self, email: str) -> User | None:
        return self.repository.get_by_email(email.strip().lower())

    def set_model(self, user: User, model: str | None) -> str:
        """Valida o modelo contra a allowlist; `None` restaura o default."""
        resolved = model.strip() if model else DEFAULT_USER_MODEL
        if resolved not in allowed_models():
            raise ValueError(f"modelo não suportado: {resolved}")
        user.model = resolved
        return resolved

    def resolve_model(self, user: User) -> str:
        """Modelo efetivo do usuário; se fora da allowlist, cai para o primeiro
        permitido (defense in depth em call-time)."""
        if user.model is not None and user.model in allowed_models():
            return user.model
        models = allowed_models()
        return models[0] if models else DEFAULT_USER_MODEL


__all__ = ["DEFAULT_USER_MODEL", "UserService"]
