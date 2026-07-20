"""Fiscalizaciones realizadas en vía pública."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import ActiveUserDep, SessionDep
from app.models.enums import EstadoResultado
from app.schemas.common import ErrorResponse
from app.schemas.inspection import InspectionCreate, InspectionRead
from app.services import inspection_service

router = APIRouter()


@router.post(
    "",
    response_model=InspectionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una inspección rápida",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse, "description": "El vehículo o la placa no existen"
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ErrorResponse, "description": "Falta 'vehicle_id' o 'placa'"
        },
    },
)
async def create_inspection(
    session: SessionDep, current_user: ActiveUserDep, payload: InspectionCreate
) -> InspectionRead:
    """El vehículo se identifica por `vehicle_id` o por `placa`.

    El inspector se toma del token: nunca se acepta desde el cuerpo.
    """
    inspection = await inspection_service.create_inspection(
        session, payload, current_user=current_user
    )
    return InspectionRead.model_validate(inspection)


@router.get(
    "/recent",
    response_model=list[InspectionRead],
    summary="Últimas fiscalizaciones realizadas",
)
async def list_recent(
    session: SessionDep,
    current_user: ActiveUserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    only_mine: Annotated[
        bool, Query(description="Restringir a las del fiscalizador autenticado")
    ] = False,
    vehicle_id: Annotated[int | None, Query(ge=1)] = None,
    estado: Annotated[EstadoResultado | None, Query()] = None,
) -> list[InspectionRead]:
    inspections = await inspection_service.list_recent(
        session,
        limit=limit,
        only_mine=only_mine,
        current_user=current_user,
        vehicle_id=vehicle_id,
        estado=estado,
    )
    return [InspectionRead.model_validate(item) for item in inspections]
