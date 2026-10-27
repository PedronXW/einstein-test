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
    chunk_ids: list[int] = Field(default_factory=list)
    vector_reference: str | None = None
    status: str = "pending"
    error_detail: str | None = None
    created_at: datetime