"""Fiscalización realizada en vía pública."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SAEnum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow
from app.models.enums import EstadoResultado

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.vehicle import Vehicle


class Inspection(Base, TimestampMixin):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(primary_key=True)

    vehicle_id: Mapped[int] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inspector_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    tipo_inspeccion: Mapped[str] = mapped_column(
        String(60), nullable=False,
        comment="Ej. RUTINARIA, OPERATIVO, DENUNCIA, RENOVACION",
    )
    estado_resultado: Mapped[EstadoResultado] = mapped_column(
        SAEnum(
            EstadoResultado,
            name="estado_resultado",
            native_enum=False,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=EstadoResultado.PENDIENTE,
        nullable=False,
        index=True,
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False, index=True
    )

    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    ubicacion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitud: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitud: Mapped[float | None] = mapped_column(Float, nullable=True)

    vehicle: Mapped["Vehicle"] = relationship(back_populates="inspections")
    inspector: Mapped["User"] = relationship(back_populates="inspections")

    def __repr__(self) -> str:
        return f"<Inspection id={self.id} vehicle_id={self.vehicle_id} {self.estado_resultado}>"
