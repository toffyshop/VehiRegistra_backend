"""Enumeraciones del dominio, compartidas entre modelos y schemas."""

from enum import StrEnum


class EstadoPermiso(StrEnum):
    """Situación del permiso de circulación del vehículo."""

    VIGENTE = "VIGENTE"
    EN_TRAMITE = "EN_TRAMITE"
    VENCIDO = "VENCIDO"


class TipoVehiculo(StrEnum):
    """Categoría de vehículo asociada a la asociación gremial."""

    LIVIANO = "LIVIANO"
    MOTOCICLETA = "MOTOCICLETA"


class EstadoResultado(StrEnum):
    """Resultado de una fiscalización en vía pública."""

    APROBADO = "APROBADO"
    PENDIENTE = "PENDIENTE"
    RECHAZADO = "RECHAZADO"
