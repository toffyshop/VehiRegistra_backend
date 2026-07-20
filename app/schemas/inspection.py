"""Schemas de fiscalizaciones."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import EstadoResultado
from app.schemas.vehicle import normalize_placa


class InspectionCreate(BaseModel):
    """Inspección rápida en vía pública.

    Se identifica el vehículo por `vehicle_id` **o** por `placa`; el segundo es
    lo habitual cuando el fiscalizador escanea o digita la placa en la calle.
    """

    vehicle_id: int | None = None
    placa: str | None = None
    tipo_inspeccion: str = Field(..., min_length=3, max_length=60, examples=["RUTINARIA"])
    estado_resultado: EstadoResultado = EstadoResultado.PENDIENTE
    observaciones: str | None = Field(default=None, max_length=1000)
    ubicacion: str | None = Field(default=None, max_length=200)
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("placa")
    @classmethod
    def _normalize(cls, value: str | None) -> str | None:
        return normalize_placa(value) if value else None

    @model_validator(mode="after")
    def _require_identifier(self) -> Self:
        if self.vehicle_id is None and self.placa is None:
            raise ValueError("Debe indicar 'vehicle_id' o 'placa'.")
        return self


class InspectionVehicleBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    placa: str
    marca_modelo: str
    propietario_nombre: str


class InspectionInspectorBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    code: str


class InspectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo_inspeccion: str
    estado_resultado: EstadoResultado
    fecha: datetime
    observaciones: str | None
    ubicacion: str | None
    latitud: float | None
    longitud: float | None
    vehicle: InspectionVehicleBrief
    inspector: InspectionInspectorBrief
