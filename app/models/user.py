"""Modelo del fiscalizador municipal."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.inspection import Inspection
    from app.models.vehicle import Vehicle


class User(Base, TimestampMixin):
    """Fiscalizador que registra vehículos y realiza inspecciones."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    dni: Mapped[str] = mapped_column(String(8), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False,
        comment="Código interno del fiscalizador, ej. FIS-001",
    )
    area: Mapped[str | None] = mapped_column(
        String(120), nullable=True, comment="Área o gerencia a la que pertenece"
    )
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    vehicles: Mapped[list["Vehicle"]] = relationship(
        back_populates="created_by", foreign_keys="Vehicle.created_by_user_id"
    )
    inspections: Mapped[list["Inspection"]] = relationship(back_populates="inspector")

    def __repr__(self) -> str:
        return f"<User id={self.id} code={self.code!r} dni={self.dni!r}>"
