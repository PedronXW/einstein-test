"""Serviço de Message — orquestra CRUD sobre o repositório.

`MAX_HISTORY` é a política de histórico do RAG (fonte única — o controller
importa daqui, não define a própria constante).
"""

from einstein_test.models.message import Message
from einstein_test.repositories import MessageRepository

MAX_HISTORY = 10


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

    def list_messages_page(
        self, chat_id: int, page: int, page_size: int
    ) -> tuple[list[Message], int]:
        offset = (page - 1) * page_size
        items = self.repository.list(
            chat_id=chat_id, limit=page_size, offset=offset
        )
        total = self.repository.count(chat_id=chat_id)
        return items, total

    def delete_message(self, message_id: int) -> None:
        message = self.repository.get_by_id(message_id)
        if message is None:
            raise MessageNotFoundError(f"message {message_id} não encontrado")
        self.repository.delete(message_id)