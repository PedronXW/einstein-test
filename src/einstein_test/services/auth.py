"""Serviço de Auth — registro e login."""

from sqlalchemy.exc import IntegrityError

from einstein_test.models import User
from einstein_test.repositories import UserRepository
from einstein_test.security import hash_password, verify_password

BCRYPT_MAX_BYTES = 72


class EmailAlreadyRegistered(LookupError):
    """Lançada quando o email já existe."""


class InvalidCredentials(LookupError):
    """Lançada quando email/senha não conferem."""


class AuthService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository: UserRepository = repository

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    def register(self, email: str, password: str) -> User:
        email = self._normalize_email(email)
        if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise InvalidCredentials(
                "senha muito longa (máximo 72 bytes)"
            )
        if self.repository.get_by_email(email) is not None:
            raise EmailAlreadyRegistered(f"email já cadastrado: {email}")
        try:
            return self.repository.create(
                email=email, password_hash=hash_password(password)
            )
        except IntegrityError:
            raise EmailAlreadyRegistered(f"email já cadastrado: {email}") from None

    def authenticate(self, email: str, password: str) -> User:
        email = self._normalize_email(email)
        user = self.repository.get_by_email(email)
        if user is None:
            raise InvalidCredentials("usuário ou senha inválidos")
        if not verify_password(password, user.password_hash):
            raise InvalidCredentials("usuário ou senha inválidos")
        return user
