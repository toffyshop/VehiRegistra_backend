"""Gestión del perfil del fiscalizador y sus métricas."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models.base import utcnow
from app.models.inspection import Inspection
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.user import (
    UserCreate,
    UserMetrics,
    UserProfile,
    UserRead,
    UserUpdate,
)


async def get_by_id(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError("El fiscalizador no existe.")
    return user


async def compute_metrics(session: AsyncSession, user_id: int) -> UserMetrics:
    """Métricas de productividad en una sola consulta por agregado."""
    now = utcnow()
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_registros = await session.scalar(
        select(func.count(Vehicle.id)).where(Vehicle.created_by_user_id == user_id)
    )
    total_fiscalizaciones = await session.scalar(
        select(func.count(Inspection.id)).where(Inspection.inspector_id == user_id)
    )
    registros_mes = await session.scalar(
        select(func.count(Vehicle.id)).where(
            Vehicle.created_by_user_id == user_id,
            Vehicle.created_at >= inicio_mes,
        )
    )

    return UserMetrics(
        total_registros=total_registros or 0,
        total_fiscalizaciones=total_fiscalizaciones or 0,
        registros_mes_actual=registros_mes or 0,
    )


async def get_profile(session: AsyncSession, user: User) -> UserProfile:
    metrics = await compute_metrics(session, user.id)
    return UserProfile(**UserRead.model_validate(user).model_dump(), metrics=metrics)


async def update_profile(
    session: AsyncSession, user: User, payload: UserUpdate
) -> User:
    """Actualiza sólo los campos enviados (PATCH semántico sobre PUT)."""
    data = payload.model_dump(exclude_unset=True)

    if "email" in data and data["email"]:
        data["email"] = data["email"].lower()
        exists = await session.scalar(
            select(User.id).where(User.email == data["email"], User.id != user.id)
        )
        if exists:
            raise ConflictError("El correo electrónico ya está en uso por otro usuario.")

    for field, value in data.items():
        setattr(user, field, value)

    await session.commit()
    await session.refresh(user)
    return user


async def change_password(
    session: AsyncSession, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise UnauthorizedError("La contraseña actual es incorrecta.")

    user.hashed_password = hash_password(new_password)
    await session.commit()


async def create_user(session: AsyncSession, payload: UserCreate) -> User:
    """Alta de fiscalizador (usado por el seed y por tareas administrativas)."""
    duplicate = await session.scalar(
        select(User.id).where(
            or_(
                User.dni == payload.dni,
                User.email == payload.email.lower(),
                User.code == payload.code.upper(),
            )
        )
    )
    if duplicate:
        raise ConflictError("Ya existe un fiscalizador con ese DNI, código o email.")

    user = User(
        dni=payload.dni,
        email=payload.email.lower(),
        phone=payload.phone,
        code=payload.code.upper(),
        area=payload.area,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
