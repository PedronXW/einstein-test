"""Serviço de Chat — orquestra CRUD sobre o repositório."""

from app.models.chat import Chat
from app.repositories import ChatRepository


class ChatNotFoundError(LookupError):
    """Lançada quando um chat não existe."""


class ChatService:
    def __init__(self, repository: ChatRepository) -> None:
        self.repository: ChatRepository = repository

    def create_chat(self, name: str, description: str | None = None) -> Chat:
        return self.repository.create(name=name, description=description)

    def get_chat(self, chat_id: int) -> Chat:
        chat = self.repository.get_by_id(chat_id)
        if chat is None:
            raise ChatNotFoundError(f"chat {chat_id} não encontrado")
        return chat

    def list_chats(self) -> list[Chat]:
        return self.repository.list()

    def delete_chat(self, chat_id: int) -> None:
        chat = self.repository.get_by_id(chat_id)
        if chat is None:
            raise ChatNotFoundError(f"chat {chat_id} não encontrado")
        self.repository.delete(chat_id)