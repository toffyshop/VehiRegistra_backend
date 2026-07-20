"""Lógica de negocio de las fiscalizaciones en vía pública."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.base import utcnow
from app.models.enums import EstadoResultado
from app.models.inspection import Inspection
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.inspection import InspectionCreate

_LOAD_OPTIONS = (
    selectinload(Inspection.vehicle),
    selectinload(Inspection.inspector),
)


async def _resolve_vehicle(session: AsyncSession, payload: InspectionCreate) -> Vehicle:
    """Ubica el vehículo por id o por placa (validado en el schema)."""
    if payload.vehicle_id is not None:
        vehicle = await session.get(Vehicle, payload.vehicle_id)
        if vehicle is None:
            raise NotFoundError(
                "El vehículo indicado no existe.",
                details={"vehicle_id": payload.vehicle_id},
            )
        return vehicle

    stmt = select(Vehicle).where(Vehicle.placa == payload.placa)
    vehicle = (await session.execute(stmt)).scalar_one_or_none()
    if vehicle is None:
        raise NotFoundError(
            "La placa no está registrada en el padrón municipal. "
            "Regístrela antes de fiscalizarla.",
            details={"placa": payload.placa},
        )
    return vehicle


async def create_inspection(
    session: AsyncSession, payload: InspectionCreate, *, current_user: User
) -> Inspection:
    vehicle = await _resolve_vehicle(session, payload)

    inspection = Inspection(
        vehicle_id=vehicle.id,
        inspector_id=current_user.id,
        tipo_inspeccion=payload.tipo_inspeccion.strip().upper(),
        estado_resultado=payload.estado_resultado,
        observaciones=payload.observaciones,
        ubicacion=payload.ubicacion,
        latitud=payload.latitud,
        longitud=payload.longitud,
        fecha=utcnow(),
    )
    session.add(inspection)
    await session.commit()

    return await get_by_id(session, inspection.id)


async def get_by_id(session: AsyncSession, inspection_id: int) -> Inspection:
    stmt = (
        select(Inspection).options(*_LOAD_OPTIONS).where(Inspection.id == inspection_id)
    )
    inspection = (await session.execute(stmt)).scalar_one_or_none()
    if inspection is None:
        raise NotFoundError(
            "La inspección no existe.", details={"inspection_id": inspection_id}
        )
    return inspection


async def list_recent(
    session: AsyncSession,
    *,
    limit: int = 10,
    only_mine: bool = False,
    current_user: User | None = None,
    vehicle_id: int | None = None,
    estado: EstadoResultado | None = None,
) -> list[Inspection]:
    """Últimas fiscalizaciones, opcionalmente filtradas."""
    stmt = select(Inspection).options(*_LOAD_OPTIONS)

    if only_mine and current_user is not None:
        stmt = stmt.where(Inspection.inspector_id == current_user.id)
    if vehicle_id is not None:
        stmt = stmt.where(Inspection.vehicle_id == vehicle_id)
    if estado is not None:
        stmt = stmt.where(Inspection.estado_resultado == estado)

    stmt = stmt.order_by(Inspection.fecha.desc(), Inspection.id.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


async def count_by_vehicle(session: AsyncSession, vehicle_id: int) -> int:
    total = await session.scalar(
        select(func.count(Inspection.id)).where(Inspection.vehicle_id == vehicle_id)
    )
    return total or 0
