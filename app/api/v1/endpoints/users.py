"""Perfil del fiscalizador autenticado."""

from fastapi import APIRouter, status

from app.api.deps import ActiveUserDep, SessionDep
from app.schemas.common import ErrorResponse, Message
from app.schemas.user import ChangePasswordRequest, UserProfile, UserRead, UserUpdate
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

    `dni` y `code` son inmutables: identifican al fiscalizador ante la municipalidad.
    """
    user = await user_service.update_profile(session, current_user, payload)
    return UserRead.model_validate(user)


@router.post(
    "/me/change-password",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Cambiar la contraseña propia",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse, "description": "La contraseña actual es incorrecta"
        },
    },
)
async def change_password(
    session: SessionDep, current_user: ActiveUserDep, payload: ChangePasswordRequest
) -> Message:
    await user_service.change_password(
        session, current_user, payload.current_password, payload.new_password
    )
    return Message(
        message="Contraseña actualizada correctamente. Vuelva a iniciar sesión."
    )
