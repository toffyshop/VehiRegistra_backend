"""Schemas de la consulta vehicular externa (SUNARP)."""

from datetime import datetime

from pydantic import BaseModel, Field


class SunarpOwner(BaseModel):
    nombre_completo: str
    dni: str
    direccion: str | None = None


class SunarpVehicleData(BaseModel):
    """Datos que el formulario de registro autocompleta a partir de la placa."""

    placa: str
    marca: str
    modelo: str
    marca_modelo: str = Field(..., description="Concatenación lista para el formulario")
    anio: int | None = None
    color: str | None = None
    nro_motor: str | None = None
    nro_serie: str | None = None
    categoria: str | None = Field(default=None, examples=["L5", "M1"])
    estado_registral: str | None = None
    propietario: SunarpOwner
    alerta_robo: bool = False


class SunarpResponse(BaseModel):
    success: bool = True
    source: str = Field(..., description="Origen del dato: 'mock' o 'sunarp'")
    consulted_at: datetime
    ya_registrado: bool = Field(
        ..., description="True si la placa ya existe en el padrón municipal"
    )
    data: SunarpVehicleData
