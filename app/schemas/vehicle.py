"""Schemas de vehículos y mototaxis."""

import re
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import EstadoPermiso
from app.schemas.association import AssociationRead

# Formato de placa peruano: 3 caracteres + 3 alfanuméricos (ABC-123, A3H-451, 1234-5A).
PLACA_PATTERN = re.compile(r"^[A-Z0-9]{3}-?[A-Z0-9]{3}$")

Anio = Annotated[int, Field(ge=1950, le=date.today().year + 1)]


def normalize_placa(value: str) -> str:
    """Mayúsculas, sin espacios y con guion canónico: 'a3h451' -> 'A3H-451'."""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    if not PLACA_PATTERN.match(cleaned):
        raise ValueError(
            "Placa inválida. Use el formato de 6 caracteres alfanuméricos, ej. A3H-451."
        )
    return f"{cleaned[:3]}-{cleaned[3:]}"


class VehicleBase(BaseModel):
    propietario_nombre: str = Field(..., min_length=3, max_length=160)
    propietario_dni: str = Field(..., pattern=r"^\d{8}$")
    marca_modelo: str = Field(..., min_length=2, max_length=120)
    nro_motor: str | None = Field(default=None, max_length=50)
    asociacion_id: int | None = None
    anio: Anio | None = None
    color: str | None = Field(default=None, max_length=40)
    en_circulacion: bool = True
    alerta_robo: bool = False


class VehicleCreate(VehicleBase):
    """Cuerpo del registro. Se recibe como form-data junto con la fotografía."""

    placa: str
    estado_permiso: EstadoPermiso = EstadoPermiso.EN_TRAMITE
    fecha_emision: date | None = None
    fecha_vencimiento: date | None = None

    @field_validator("placa")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return normalize_placa(value)


class VehicleUpdate(BaseModel):
    """Actualización parcial. Todos los campos son opcionales."""

    propietario_nombre: str | None = Field(default=None, min_length=3, max_length=160)
    propietario_dni: str | None = Field(default=None, pattern=r"^\d{8}$")
    marca_modelo: str | None = Field(default=None, min_length=2, max_length=120)
    nro_motor: str | None = Field(default=None, max_length=50)
    asociacion_id: int | None = None
    anio: Anio | None = None
    color: str | None = Field(default=None, max_length=40)
    estado_permiso: EstadoPermiso | None = None
    fecha_emision: date | None = None
    fecha_vencimiento: date | None = None
    en_circulacion: bool | None = None
    alerta_robo: bool | None = None


class VehicleRenew(BaseModel):
    """Renovación del permiso de circulación."""

    fecha_vencimiento: date = Field(..., description="Nueva fecha de vencimiento")
    fecha_emision: date | None = None
    observacion: str | None = Field(default=None, max_length=300)


class VehicleOwnerBrief(BaseModel):
    """Datos del fiscalizador que registró el vehículo."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    code: str


class VehicleRead(BaseModel):
    """Vista de listado."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    placa: str
    codigo_qr: str
    propietario_nombre: str
    propietario_dni: str
    marca_modelo: str
    anio: int | None
    color: str | None
    estado_permiso: EstadoPermiso
    fecha_vencimiento: date | None
    en_circulacion: bool
    alerta_robo: bool
    photo_url: str | None
    created_at: datetime


class VehicleDetail(VehicleRead):
    """Vista de detalle: agrega relaciones y campos administrativos."""

    nro_motor: str | None
    fecha_emision: date | None
    asociacion: AssociationRead | None = None
    created_by: VehicleOwnerBrief | None = None
    total_inspecciones: int = 0
    dias_para_vencimiento: int | None = Field(
        default=None, description="Negativo si el permiso ya venció"
    )
