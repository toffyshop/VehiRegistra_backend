"""Agregados para el dashboard y el módulo de reportes."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.association import Association
from app.models.base import today, utcnow
from app.models.enums import EstadoPermiso, EstadoResultado
from app.models.inspection import Inspection
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.dashboard import (
    AssociationBreakdown,
    DashboardSummary,
    EstadoBreakdown,
    ReportStats,
    SystemStatus,
    VehicleTypeBreakdown,
)
from app.schemas.inspection import InspectionRead
from app.services import inspection_service

DIAS_POR_VENCER = 30


def _inicio_del_dia() -> datetime:
    return utcnow().replace(hour=0, minute=0, second=0, microsecond=0)


async def _estado_sistema(session: AsyncSession) -> SystemStatus:
    """Comprueba la conectividad real con la base de datos."""
    try:
        await session.execute(select(1))
        database = "online"
    except Exception:  # noqa: BLE001 - el estado degradado no debe tumbar el endpoint
        database = "offline"

    return SystemStatus(
        database=database,
        sunarp_service="online",  # el mock siempre responde
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
        server_time=datetime.now(timezone.utc),
    )


async def get_summary(session: AsyncSession, *, current_user: User) -> DashboardSummary:
    inicio_dia = _inicio_del_dia()
    limite_vencimiento = today() + timedelta(days=DIAS_POR_VENCER)

    inspecciones_hoy = await session.scalar(
        select(func.count(Inspection.id)).where(Inspection.fecha >= inicio_dia)
    )
    registros_hoy = await session.scalar(
        select(func.count(Vehicle.id)).where(Vehicle.created_at >= inicio_dia)
    )
    mis_registros_hoy = await session.scalar(
        select(func.count(Vehicle.id)).where(
            Vehicle.created_at >= inicio_dia,
            Vehicle.created_by_user_id == current_user.id,
        )
    )
    inspecciones_pendientes = await session.scalar(
        select(func.count(Inspection.id)).where(
            Inspection.estado_resultado == EstadoResultado.PENDIENTE
        )
    )
    total_vehiculos = await session.scalar(select(func.count(Vehicle.id)))
    alertas_robo = await session.scalar(
        select(func.count(Vehicle.id)).where(Vehicle.alerta_robo.is_(True))
    )
    por_vencer = await session.scalar(
        select(func.count(Vehicle.id)).where(
            Vehicle.estado_permiso == EstadoPermiso.VIGENTE,
            Vehicle.fecha_vencimiento.is_not(None),
            Vehicle.fecha_vencimiento <= limite_vencimiento,
            Vehicle.fecha_vencimiento >= today(),
        )
    )

    return DashboardSummary(
        inspecciones_hoy=inspecciones_hoy or 0,
        registros_hoy=registros_hoy or 0,
        inspecciones_pendientes=inspecciones_pendientes or 0,
        total_vehiculos=total_vehiculos or 0,
        alertas_robo_activas=alertas_robo or 0,
        permisos_por_vencer=por_vencer or 0,
        mis_registros_hoy=mis_registros_hoy or 0,
        system_status=await _estado_sistema(session),
    )


async def _conteo_por_estado(session: AsyncSession) -> dict[EstadoPermiso, int]:
    stmt = select(Vehicle.estado_permiso, func.count(Vehicle.id)).group_by(
        Vehicle.estado_permiso
    )
    rows = (await session.execute(stmt)).all()
    conteo = {estado: 0 for estado in EstadoPermiso}
    for estado, total in rows:
        conteo[EstadoPermiso(estado)] = total
    return conteo


async def _desglose_por_asociacion(session: AsyncSession) -> list[AssociationBreakdown]:
    """Un LEFT JOIN con agregados condicionales: una sola ida a la base."""
    vigentes = func.sum(
        case((Vehicle.estado_permiso == EstadoPermiso.VIGENTE, 1), else_=0)
    )
    vencidos = func.sum(
        case((Vehicle.estado_permiso == EstadoPermiso.VENCIDO, 1), else_=0)
    )

    stmt = (
        select(
            Association.id,
            Association.nombre,
            Association.tipo_vehiculo,
            func.count(Vehicle.id).label("total"),
            vigentes.label("vigentes"),
            vencidos.label("vencidos"),
        )
        .select_from(Association)
        .outerjoin(Vehicle, Vehicle.asociacion_id == Association.id)
        .group_by(Association.id, Association.nombre, Association.tipo_vehiculo)
        .order_by(func.count(Vehicle.id).desc())
    )
    rows = (await session.execute(stmt)).all()

    desglose = [
        AssociationBreakdown(
            asociacion_id=row.id,
            nombre=row.nombre,
            tipo_vehiculo=row.tipo_vehiculo,
            total=row.total or 0,
            vigentes=int(row.vigentes or 0),
            vencidos=int(row.vencidos or 0),
        )
        for row in rows
    ]

    # Vehículos sin asociación: no aparecen en el join anterior.
    sin_asociacion = await session.scalar(
        select(func.count(Vehicle.id)).where(Vehicle.asociacion_id.is_(None))
    )
    if sin_asociacion:
        vigentes_sa = await session.scalar(
            select(func.count(Vehicle.id)).where(
                Vehicle.asociacion_id.is_(None),
                Vehicle.estado_permiso == EstadoPermiso.VIGENTE,
            )
        )
        vencidos_sa = await session.scalar(
            select(func.count(Vehicle.id)).where(
                Vehicle.asociacion_id.is_(None),
                Vehicle.estado_permiso == EstadoPermiso.VENCIDO,
            )
        )
        desglose.append(
            AssociationBreakdown(
                asociacion_id=None,
                nombre="SIN ASOCIACIÓN",
                tipo_vehiculo=None,
                total=sin_asociacion,
                vigentes=vigentes_sa or 0,
                vencidos=vencidos_sa or 0,
            )
        )

    return desglose


async def _desglose_por_tipo(session: AsyncSession) -> list[VehicleTypeBreakdown]:
    stmt = (
        select(Association.tipo_vehiculo, func.count(Vehicle.id))
        .select_from(Vehicle)
        .join(Association, Vehicle.asociacion_id == Association.id)
        .group_by(Association.tipo_vehiculo)
    )
    rows = (await session.execute(stmt)).all()
    desglose = [
        VehicleTypeBreakdown(tipo_vehiculo=tipo, total=total) for tipo, total in rows
    ]

    sin_tipo = await session.scalar(
        select(func.count(Vehicle.id)).where(Vehicle.asociacion_id.is_(None))
    )
    if sin_tipo:
        desglose.append(VehicleTypeBreakdown(tipo_vehiculo=None, total=sin_tipo))

    return desglose


async def get_stats(session: AsyncSession, *, recientes: int = 5) -> ReportStats:
    conteo = await _conteo_por_estado(session)
    total = sum(conteo.values())

    desglose_estado = [
        EstadoBreakdown(
            estado_permiso=estado,
            total=cantidad,
            porcentaje=round(cantidad * 100 / total, 2) if total else 0.0,
        )
        for estado, cantidad in conteo.items()
    ]

    total_inspecciones = await session.scalar(select(func.count(Inspection.id)))
    inspecciones = await inspection_service.list_recent(session, limit=recientes)

    return ReportStats(
        total_registrados=total,
        permisos_vigentes=conteo[EstadoPermiso.VIGENTE],
        permisos_en_tramite=conteo[EstadoPermiso.EN_TRAMITE],
        permisos_vencidos=conteo[EstadoPermiso.VENCIDO],
        total_inspecciones=total_inspecciones or 0,
        desglose_por_estado=desglose_estado,
        desglose_por_asociacion=await _desglose_por_asociacion(session),
        desglose_por_tipo_vehiculo=await _desglose_por_tipo(session),
        inspecciones_recientes=[
            InspectionRead.model_validate(item) for item in inspecciones
        ],
        generated_at=datetime.now(timezone.utc),
    )
