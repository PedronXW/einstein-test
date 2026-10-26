"""Schemas Pydantic de File."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    name: str
    url: str
    type: str | None = None
    size: int = Field(ge=0)
    created_at: datetime