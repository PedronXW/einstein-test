"""Serviço de Chat — orquestra CRUD sobre o repositório."""

from einstein_test.models.chat import Chat
from einstein_test.repositories import ChatRepository


class ChatNotFoundError(LookupError):
    """Lançada quando um chat não existe (ou não pertence ao usuário)."""


class ChatService:
    def __init__(self, repository: ChatRepository) -> None:
        self.repository: ChatRepository = repository

    def create_chat(
        self, user_id: int, name: str, description: str | None = None
    ) -> Chat:
        return self.repository.create(
            user_id=user_id, name=name, description=description
        )

    def get_chat(self, chat_id: int, user_id: int) -> Chat:
        chat = self.repository.get_by_id(chat_id, user_id)
        if chat is None:
            raise ChatNotFoundError(
                f"chat {chat_id} não encontrado para o usuário {user_id}"
            )
        return chat

    def list_chats(self, user_id: int) -> list[Chat]:
        return self.repository.list(user_id=user_id)

    def list_chats_page(
        self, user_id: int, page: int, page_size: int
    ) -> tuple[list[Chat], int]:
        offset = (page - 1) * page_size
        items = self.repository.list(
            user_id=user_id, limit=page_size, offset=offset
        )
        total = self.repository.count(user_id=user_id)
        return items, total

    def delete_chat(self, chat_id: int, user_id: int) -> None:
        chat = self.repository.get_by_id(chat_id, user_id)
        if chat is None:
            raise ChatNotFoundError(
                f"chat {chat_id} não encontrado para o usuário {user_id}"
            )
        self.repository.delete(chat_id)