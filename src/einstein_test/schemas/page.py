"""Schema genérico de resposta paginada (envelope padrão dos list endpoints)."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    total_pages: int

    @classmethod
    def build(
        cls,
        items: list[T],
        *,
        total: int,
        page: int,
        page_size: int,
    ) -> "Page[T]":
        total_pages = (total + page_size - 1) // page_size if total else 0
        return cls(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )
