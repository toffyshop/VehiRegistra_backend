"""Integración con la consulta vehicular externa (SUNARP)."""

from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.deps import ActiveUserDep, SessionDep
from app.schemas.common import ErrorResponse
from app.schemas.sunarp import SunarpResponse
from app.services import sunarp_service

router = APIRouter()


@router.get(
    "/sunarp/{placa}",
    response_model=SunarpResponse,
    summary="Consultar una placa para autocompletar el formulario",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Placa con formato inválido o sin datos registrales",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": "El servicio externo no respondió",
        },
    },
)
async def consultar_sunarp(
    session: SessionDep,
    current_user: ActiveUserDep,
    placa: Annotated[str, Path(min_length=6, max_length=10, examples=["A3H-451"])],
) -> SunarpResponse:
    """Devuelve datos del vehículo y su propietario a partir de la placa.

    La respuesta incluye `ya_registrado`, que permite a la app avisar al
    fiscalizador antes de crear un duplicado en el padrón.
    """
    return await sunarp_service.consultar_placa(session, placa)
