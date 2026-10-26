"""Serviço de Message — orquestra CRUD sobre o repositório."""

from app.models.message import Message
from app.repositories import MessageRepository


class MessageNotFoundError(LookupError):
    """Lançada quando uma message não existe."""


class MessageService:
    def __init__(self, repository: MessageRepository) -> None:
        self.repository: MessageRepository = repository

    def create_message(
        self, chat_id: int, content: str, role: str | None = None
    ) -> Message:
        return self.repository.create(chat_id=chat_id, content=content, role=role)

    def get_message(self, message_id: int) -> Message:
        message = self.repository.get_by_id(message_id)
        if message is None:
            raise MessageNotFoundError(f"message {message_id} não encontrado")
        return message

    def list_messages(self, chat_id: int) -> list[Message]:
        return self.repository.list(chat_id=chat_id)

    def delete_message(self, message_id: int) -> None:
        message = self.repository.get_by_id(message_id)
        if message is None:
            raise MessageNotFoundError(f"message {message_id} não encontrado")
        self.repository.delete(message_id)