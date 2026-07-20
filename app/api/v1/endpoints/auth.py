"""Autenticación de fiscalizadores."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import ActiveUserDep, SessionDep
from app.schemas.auth import LoginRequest, Token
from app.schemas.common import ErrorResponse
from app.schemas.user import UserRead
from app.services import auth_service

router = APIRouter()


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión (OAuth2 Password Flow)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse, "description": "Credenciales inválidas"
        },
    },
)
async def login(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """Emite un JWT.

    El campo `username` acepta **DNI**, **código de fiscalizador** o **email**.
    Se envía como `application/x-www-form-urlencoded` según el estándar OAuth2.
    """
    return await auth_service.login(session, form_data.username, form_data.password)


@router.post(
    "/login/json",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Iniciar sesión enviando JSON",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": ErrorResponse, "description": "Credenciales inválidas"
        },
    },
)
async def login_json(session: SessionDep, payload: LoginRequest) -> Token:
    """Variante JSON del login con correo electrónico.

    Más cómoda desde Retrofit/Kotlin que el form-urlencoded de OAuth2.
    """
    return await auth_service.login(session, payload.email, payload.password)


@router.get(
    "/verify",
    response_model=UserRead,
    summary="Verificar la vigencia del token actual",
)
async def verify_token(current_user: ActiveUserDep) -> UserRead:
    """Permite al cliente móvil saber si debe reautenticar al abrir la app."""
    return UserRead.model_validate(current_user)
