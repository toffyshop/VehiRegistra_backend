"""Dependencias reutilizables: sesión de base de datos, usuario autenticado
y parámetros de paginación."""

from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    scheme_name="JWT",
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
TokenDep = Annotated[str, Depends(oauth2_scheme)]


async def get_current_user(session: SessionDep, token: TokenDep) -> User:
    """Resuelve el fiscalizador autenticado a partir del Bearer token."""
    payload = decode_access_token(token)
    if payload is None:
        raise UnauthorizedError("Token inválido o expirado.")

    subject = payload.get("sub")
    if subject is None or not str(subject).isdigit():
        raise UnauthorizedError("Token malformado.")

    user = await session.get(User, int(subject))
    if user is None:
        raise UnauthorizedError("El fiscalizador asociado al token ya no existe.")

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_current_active_user(current_user: CurrentUserDep) -> User:
    if not current_user.is_active:
        raise ForbiddenError("La cuenta del fiscalizador está desactivada.")
    return current_user


ActiveUserDep = Annotated[User, Depends(get_current_active_user)]


class PaginationParams:
    """Parámetros de paginación compartidos por los listados."""

    def __init__(
        self,
        page: Annotated[int, Query(ge=1, description="Página, base 1")] = 1,
        size: Annotated[
            int, Query(ge=1, le=100, description="Registros por página (máx. 100)")
        ] = 20,
    ) -> None:
        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


PaginationDep = Annotated[PaginationParams, Depends(PaginationParams)]
