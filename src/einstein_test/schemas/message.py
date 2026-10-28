"""Schemas Pydantic de Message."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    role: str | None = Field(default=None, max_length=50)

    @field_validator("content")
    @classmethod
    def _content_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("conteúdo não pode ser só espaços")
        return v


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    content: str
    role: str | None = None
    created_at: datetime