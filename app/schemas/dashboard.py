"""Schemas del dashboard y del módulo de reportes."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import EstadoPermiso, TipoVehiculo
from app.schemas.inspection import InspectionRead


class SystemStatus(BaseModel):
    database: str = Field(..., examples=["online", "offline"])
    sunarp_service: str = Field(..., examples=["online", "degraded"])
    environment: str
    version: str
    server_time: datetime


class DashboardSummary(BaseModel):
    """GET /dashboard/summary — tarjetas de la pantalla principal."""

    inspecciones_hoy: int
    registros_hoy: int
    inspecciones_pendientes: int
    total_vehiculos: int
    alertas_robo_activas: int
    permisos_por_vencer: int = Field(..., description="Vencen en los próximos 30 días")
    mis_registros_hoy: int = Field(..., description="Del fiscalizador autenticado")
    system_status: SystemStatus


class AssociationBreakdown(BaseModel):
    asociacion_id: int | None
    nombre: str
    tipo_vehiculo: TipoVehiculo | None
    total: int
    vigentes: int
    vencidos: int


class VehicleTypeBreakdown(BaseModel):
    tipo_vehiculo: TipoVehiculo | None
    total: int


class EstadoBreakdown(BaseModel):
    estado_permiso: EstadoPermiso
    total: int
    porcentaje: float


class ReportStats(BaseModel):
    """GET /reports/stats — métricas globales del padrón."""

    total_registrados: int
    permisos_vigentes: int
    permisos_en_tramite: int
    permisos_vencidos: int
    total_inspecciones: int
    desglose_por_estado: list[EstadoBreakdown]
    desglose_por_asociacion: list[AssociationBreakdown]
    desglose_por_tipo_vehiculo: list[VehicleTypeBreakdown]
    inspecciones_recientes: list[InspectionRead]
    generated_at: datetime
