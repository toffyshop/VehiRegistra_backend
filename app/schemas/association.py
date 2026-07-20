"""Schemas de asociaciones gremiales."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TipoVehiculo


class AssociationBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=160)
    tipo_vehiculo: TipoVehiculo


class AssociationCreate(AssociationBase):
    pass


class AssociationRead(AssociationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
