"""Schemas Pydantic de Message."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    role: str | None = Field(default=None, max_length=50)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    content: str
    role: str | None = None
    created_at: datetime