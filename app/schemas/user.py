"""Schemas del fiscalizador."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field

DNI = Annotated[str, Field(pattern=r"^\d{8}$", description="DNI peruano de 8 dígitos")]
Phone = Annotated[str, Field(min_length=6, max_length=20)]
Password = Annotated[str, Field(min_length=8, max_length=72)]


class UserBase(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=160)
    email: EmailStr
    phone: Phone | None = None
    area: str | None = Field(default=None, max_length=120)


class UserCreate(UserBase):
    dni: DNI
    code: str = Field(..., min_length=3, max_length=20)
    password: Password


class UserUpdate(BaseModel):
    """Campos editables del propio perfil.

    DNI, código y teléfono son inmutables: los dos primeros identifican al
    fiscalizador y el teléfono se retiró de la pantalla "Editar perfil" en el
    diseño final. Un `phone` enviado por el cliente se ignora (`extra="ignore"`).
    """

    model_config = ConfigDict(extra="ignore")

    full_name: str | None = Field(default=None, min_length=3, max_length=160)
    email: EmailStr | None = None
    area: str | None = Field(default=None, max_length=120)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dni: str
    code: str
    is_active: bool
    created_at: datetime


class UserMetrics(BaseModel):
    """Métricas de productividad del fiscalizador."""

    total_registros: int = Field(..., description="Vehículos registrados por el usuario")
    total_fiscalizaciones: int = Field(..., description="Inspecciones realizadas")
    registros_mes_actual: int = Field(..., description="Vehículos registrados este mes")


class UserProfile(UserRead):
    """Perfil devuelto por GET /users/me."""

    metrics: UserMetrics
