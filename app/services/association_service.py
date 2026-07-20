"""Catálogo de asociaciones gremiales (alimenta el selector del formulario)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.models.association import Association
from app.models.enums import TipoVehiculo
from app.schemas.association import AssociationCreate


async def list_associations(
    session: AsyncSession, *, tipo_vehiculo: TipoVehiculo | None = None
) -> list[Association]:
    stmt = select(Association).where(Association.is_active.is_(True))
    if tipo_vehiculo is not None:
        stmt = stmt.where(Association.tipo_vehiculo == tipo_vehiculo)

    result = await session.execute(stmt.order_by(Association.nombre))
    return list(result.scalars().all())


async def create_association(
    session: AsyncSession, payload: AssociationCreate
) -> Association:
    nombre = payload.nombre.strip().upper()
    exists = await session.scalar(
        select(Association.id).where(Association.nombre == nombre)
    )
    if exists:
        raise ConflictError(f"Ya existe una asociación con el nombre '{nombre}'.")

    association = Association(nombre=nombre, tipo_vehiculo=payload.tipo_vehiculo)
    session.add(association)
    await session.commit()
    await session.refresh(association)
    return association
