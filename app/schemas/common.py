"""Schemas transversales: paginación, mensajes y envoltorio de error."""

from datetime import datetime
from math import ceil
from typing import Any, Generic, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Message(BaseModel):
    """Respuesta simple para operaciones sin cuerpo de recurso."""

    success: bool = True
    message: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    """Forma exacta que devuelven los manejadores globales de excepciones."""

    success: bool = False
    error: ErrorDetail
    path: str
    timestamp: datetime


class PageMeta(BaseModel):
    total: int = Field(..., description="Total de registros que cumplen el filtro")
    page: int = Field(..., description="Página actual, base 1")
    size: int = Field(..., description="Tamaño de página solicitado")
    pages: int = Field(..., description="Cantidad total de páginas")
    has_next: bool
    has_prev: bool


class Page(BaseModel, Generic[T]):
    """Contenedor genérico de resultados paginados."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    meta: PageMeta

    @classmethod
    def create(cls, items: list[T], *, total: int, page: int, size: int) -> Self:
        pages = ceil(total / size) if size else 0
        return cls(
            items=items,
            meta=PageMeta(
                total=total,
                page=page,
                size=size,
                pages=pages,
                has_next=page < pages,
                has_prev=page > 1,
            ),
        )
