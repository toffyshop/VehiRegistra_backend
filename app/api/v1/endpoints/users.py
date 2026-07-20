"""Perfil del fiscalizador autenticado."""

from fastapi import APIRouter, status

from app.api.deps import ActiveUserDep, SessionDep
from app.schemas.common import ErrorResponse
from app.schemas.user import UserProfile, UserRead, UserUpdate
from app.services import user_service

router = APIRouter()


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Perfil del fiscalizador actual con sus métricas",
)
async def read_me(session: SessionDep, current_user: ActiveUserDep) -> UserProfile:
    """Incluye `total_registros`, `total_fiscalizaciones` y `registros_mes_actual`."""
    return await user_service.get_profile(session, current_user)


@router.put(
    "/me",
    response_model=UserRead,
    summary="Editar el perfil propio",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse, "description": "El email ya está en uso"
        },
    },
)
async def update_me(
    session: SessionDep, current_user: ActiveUserDep, payload: UserUpdate
) -> UserRead:
    """Sólo se modifican los campos presentes en el cuerpo.

    `dni`, `code` y `phone` son inmutables desde la app: los dos primeros
    identifican al fiscalizador ante la municipalidad y el teléfono se retiró
    de la pantalla de edición según el diseño final.
    """
    user = await user_service.update_profile(session, current_user, payload)
    return UserRead.model_validate(user)
