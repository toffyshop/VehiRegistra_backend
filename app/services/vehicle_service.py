"""Lógica de negocio del padrón vehicular."""

import uuid
from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.models.association import Association
from app.models.base import today
from app.models.enums import EstadoPermiso
from app.models.inspection import Inspection
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleDetail,
    VehicleRenew,
    VehicleUpdate,
    normalize_placa,
)

# Relaciones que necesita la vista de detalle.
_DETAIL_OPTIONS = (
    selectinload(Vehicle.asociacion),
    selectinload(Vehicle.created_by),
)


def _apply_expiry_state(vehicle: Vehicle) -> Vehicle:
    """Degrada a VENCIDO un permiso VIGENTE cuya fecha ya pasó.

    Evita depender de un job nocturno: el estado se corrige en cada lectura.
    """
    if (
        vehicle.estado_permiso is EstadoPermiso.VIGENTE
        and vehicle.fecha_vencimiento is not None
        and vehicle.fecha_vencimiento < today()
    ):
        vehicle.estado_permiso = EstadoPermiso.VENCIDO
    return vehicle


async def _ensure_placa_disponible(session: AsyncSession, placa: str) -> None:
    exists = await session.scalar(select(Vehicle.id).where(Vehicle.placa == placa))
    if exists:
        raise ConflictError(
            f"La placa {placa} ya se encuentra registrada en el padrón.",
            details={"placa": placa, "vehicle_id": exists},
        )


async def _ensure_asociacion_valida(session: AsyncSession, asociacion_id: int | None) -> None:
    if asociacion_id is None:
        return
    exists = await session.scalar(
        select(Association.id).where(Association.id == asociacion_id)
    )
    if not exists:
        raise NotFoundError(
            "La asociación indicada no existe.",
            details={"asociacion_id": asociacion_id},
        )


async def create_vehicle(
    session: AsyncSession,
    payload: VehicleCreate,
    *,
    current_user: User,
    photo_url: str | None = None,
) -> Vehicle:
    await _ensure_placa_disponible(session, payload.placa)
    await _ensure_asociacion_valida(session, payload.asociacion_id)

    data = payload.model_dump()
    vehicle = Vehicle(
        **data,
        codigo_qr=uuid.uuid4().hex,
        photo_url=photo_url,
        created_by_user_id=current_user.id,
    )
    _apply_expiry_state(vehicle)

    session.add(vehicle)
    await session.commit()
    await session.refresh(vehicle)
    return vehicle


def _build_list_query(
    *,
    estado: EstadoPermiso | None,
    search: str | None,
    asociacion_id: int | None,
    solo_alertas: bool,
) -> Select:
    stmt = select(Vehicle)

    if estado is not None:
        stmt = stmt.where(Vehicle.estado_permiso == estado)

    if asociacion_id is not None:
        stmt = stmt.where(Vehicle.asociacion_id == asociacion_id)

    if solo_alertas:
        stmt = stmt.where(Vehicle.alerta_robo.is_(True))

    if search:
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Vehicle.placa).like(term),
                func.lower(Vehicle.propietario_dni).like(term),
                func.lower(Vehicle.propietario_nombre).like(term),
                func.lower(Vehicle.marca_modelo).like(term),
            )
        )

    return stmt


async def list_vehicles(
    session: AsyncSession,
    *,
    page: int = 1,
    size: int = 20,
    estado: EstadoPermiso | None = None,
    search: str | None = None,
    asociacion_id: int | None = None,
    solo_alertas: bool = False,
) -> tuple[list[Vehicle], int]:
    """Devuelve (página de vehículos, total sin paginar)."""
    stmt = _build_list_query(
        estado=estado,
        search=search,
        asociacion_id=asociacion_id,
        solo_alertas=solo_alertas,
    )

    total = await session.scalar(
        select(func.count()).select_from(stmt.subquery())
    )

    paged = (
        stmt.options(*_DETAIL_OPTIONS)
        .order_by(Vehicle.created_at.desc(), Vehicle.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await session.execute(paged)
    vehicles = [_apply_expiry_state(v) for v in result.scalars().unique().all()]

    return vehicles, total or 0


async def get_by_id(session: AsyncSession, vehicle_id: int) -> Vehicle:
    stmt = select(Vehicle).options(*_DETAIL_OPTIONS).where(Vehicle.id == vehicle_id)
    vehicle = (await session.execute(stmt)).scalar_one_or_none()
    if vehicle is None:
        raise NotFoundError(
            "El vehículo no existe.", details={"vehicle_id": vehicle_id}
        )
    return _apply_expiry_state(vehicle)


async def get_by_placa_o_qr(session: AsyncSession, identificador: str) -> Vehicle:
    """Resuelve un vehículo por placa o por el código impreso en el QR."""
    raw = identificador.strip()

    try:
        placa = normalize_placa(raw)
    except ValueError:
        placa = None  # no tiene forma de placa: se buscará sólo como código QR

    stmt = select(Vehicle).options(*_DETAIL_OPTIONS)
    if placa is not None:
        stmt = stmt.where(or_(Vehicle.placa == placa, Vehicle.codigo_qr == raw))
    else:
        stmt = stmt.where(Vehicle.codigo_qr == raw)

    vehicle = (await session.execute(stmt)).scalar_one_or_none()
    if vehicle is None:
        raise NotFoundError(
            "No se encontró ningún vehículo con esa placa o código QR.",
            details={"identificador": raw},
        )
    return _apply_expiry_state(vehicle)


async def update_vehicle(
    session: AsyncSession, vehicle_id: int, payload: VehicleUpdate
) -> Vehicle:
    vehicle = await get_by_id(session, vehicle_id)
    data = payload.model_dump(exclude_unset=True)

    if "asociacion_id" in data:
        await _ensure_asociacion_valida(session, data["asociacion_id"])

    for field, value in data.items():
        setattr(vehicle, field, value)

    # Si el usuario fijó explícitamente el estado, se respeta su decisión.
    if "estado_permiso" not in data:
        _apply_expiry_state(vehicle)

    await session.commit()
    await session.refresh(vehicle)
    return await get_by_id(session, vehicle.id)


async def renew_permit(
    session: AsyncSession, vehicle_id: int, payload: VehicleRenew
) -> Vehicle:
    """Renueva el permiso: fija vencimiento futuro y deja el vehículo VIGENTE."""
    vehicle = await get_by_id(session, vehicle_id)

    if payload.fecha_vencimiento <= today():
        raise ConflictError(
            "La nueva fecha de vencimiento debe ser posterior a la fecha actual.",
            details={"fecha_vencimiento": payload.fecha_vencimiento.isoformat()},
        )

    vehicle.fecha_emision = payload.fecha_emision or today()
    vehicle.fecha_vencimiento = payload.fecha_vencimiento
    vehicle.estado_permiso = EstadoPermiso.VIGENTE
    vehicle.en_circulacion = True

    await session.commit()
    await session.refresh(vehicle)
    return await get_by_id(session, vehicle.id)


async def set_photo(session: AsyncSession, vehicle: Vehicle, photo_url: str) -> Vehicle:
    vehicle.photo_url = photo_url
    await session.commit()
    await session.refresh(vehicle)
    return vehicle


def _dias_para_vencimiento(fecha: date | None) -> int | None:
    return (fecha - today()).days if fecha is not None else None


async def to_detail(session: AsyncSession, vehicle: Vehicle) -> VehicleDetail:
    """Compone la vista de detalle con datos derivados."""
    total_inspecciones = await session.scalar(
        select(func.count(Inspection.id)).where(Inspection.vehicle_id == vehicle.id)
    )

    detail = VehicleDetail.model_validate(vehicle)
    detail.total_inspecciones = total_inspecciones or 0
    detail.dias_para_vencimiento = _dias_para_vencimiento(vehicle.fecha_vencimiento)
    return detail
