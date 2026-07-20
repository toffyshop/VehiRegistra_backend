"""Vehículo / mototaxi registrado en el padrón municipal."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import EstadoPermiso

if TYPE_CHECKING:
    from app.models.association import Association
    from app.models.inspection import Inspection
    from app.models.user import User


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(primary_key=True)

    placa: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    codigo_qr: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False,
        comment="Identificador impreso en la calcomanía; permite consulta por QR",
    )

    propietario_nombre: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    propietario_dni: Mapped[str] = mapped_column(String(8), index=True, nullable=False)

    marca_modelo: Mapped[str] = mapped_column(String(120), nullable=False)
    nro_motor: Mapped[str | None] = mapped_column(String(50), nullable=True)
    anio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    color: Mapped[str | None] = mapped_column(String(40), nullable=True)

    asociacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("associations.id", ondelete="SET NULL"), nullable=True, index=True
    )

    estado_permiso: Mapped[EstadoPermiso] = mapped_column(
        SAEnum(
            EstadoPermiso,
            name="estado_permiso",
            native_enum=False,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=EstadoPermiso.EN_TRAMITE,
        nullable=False,
        index=True,
    )
    # No están en el enunciado, pero sin fecha de vencimiento no es posible
    # calcular "permisos vencidos" ni implementar la renovación del permiso.
    fecha_emision: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    en_circulacion: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    alerta_robo: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    asociacion: Mapped["Association | None"] = relationship(back_populates="vehicles")
    created_by: Mapped["User"] = relationship(
        back_populates="vehicles", foreign_keys=[created_by_user_id]
    )
    inspections: Mapped[list["Inspection"]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Vehicle id={self.id} placa={self.placa!r} estado={self.estado_permiso}>"
