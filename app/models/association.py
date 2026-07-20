"""Asociación gremial de transportistas (mototaxis / vehículos livianos)."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import TipoVehiculo

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle


class Association(Base, TimestampMixin):
    __tablename__ = "associations"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    tipo_vehiculo: Mapped[TipoVehiculo] = mapped_column(
        SAEnum(
            TipoVehiculo,
            name="tipo_vehiculo",
            native_enum=False,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="asociacion")

    def __repr__(self) -> str:
        return f"<Association id={self.id} nombre={self.nombre!r}>"
