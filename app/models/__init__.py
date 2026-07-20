"""Modelos ORM. Importar desde aquí garantiza que todos queden registrados
en `Base.metadata` antes de crear las tablas."""

from app.models.association import Association
from app.models.base import Base, TimestampMixin, today, utcnow
from app.models.enums import EstadoPermiso, EstadoResultado, TipoVehiculo
from app.models.inspection import Inspection
from app.models.user import User
from app.models.vehicle import Vehicle

__all__ = [
    "Association",
    "Base",
    "EstadoPermiso",
    "EstadoResultado",
    "Inspection",
    "TimestampMixin",
    "TipoVehiculo",
    "User",
    "Vehicle",
    "today",
    "utcnow",
]
