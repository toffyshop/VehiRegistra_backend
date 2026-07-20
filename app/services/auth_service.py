"""Autenticación de fiscalizadores."""

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserRead


async def get_user_by_identifier(session: AsyncSession, identifier: str) -> User | None:
    """Permite iniciar sesión con DNI, código de fiscalizador o email."""
    normalized = identifier.strip()
    stmt = select(User).where(
        or_(
            User.dni == normalized,
            User.code == normalized.upper(),
            User.email == normalized.lower(),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def authenticate(session: AsyncSession, identifier: str, password: str) -> User:
    """Valida credenciales.

    Ante usuario inexistente se ejecuta igualmente un hash descartable para que
    el tiempo de respuesta no revele qué identificadores existen.
    """
    user = await get_user_by_identifier(session, identifier)

    if user is None:
        hash_password(password)
        raise UnauthorizedError("Usuario o contraseña incorrectos.")

    if not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Usuario o contraseña incorrectos.")

    if not user.is_active:
        raise UnauthorizedError("La cuenta del fiscalizador está desactivada.")

    return user


async def login(session: AsyncSession, identifier: str, password: str) -> Token:
    user = await authenticate(session, identifier, password)
    access_token, expires_in = create_access_token(
        subject=user.id,
        extra_claims={"code": user.code, "dni": user.dni},
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )
