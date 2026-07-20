"""Catálogo de asociaciones gremiales."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import ActiveUserDep, SessionDep
from app.models.enums import TipoVehiculo
from app.schemas.association import AssociationCreate, AssociationRead
from app.schemas.common import ErrorResponse
from app.services import association_service

router = APIRouter()


@router.get(
    "",
    response_model=list[AssociationRead],
    summary="Listar asociaciones activas",
)
async def list_associations(
    session: SessionDep,
    current_user: ActiveUserDep,
    tipo_vehiculo: Annotated[TipoVehiculo | None, Query()] = None,
) -> list[AssociationRead]:
    """Alimenta el selector de asociación del formulario de registro."""
    associations = await association_service.list_associations(
        session, tipo_vehiculo=tipo_vehiculo
    )
    return [AssociationRead.model_validate(item) for item in associations]


@router.post(
    "",
    response_model=AssociationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una nueva asociación",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse, "description": "El nombre ya existe"
        },
    },
)
async def create_association(
    session: SessionDep, current_user: ActiveUserDep, payload: AssociationCreate
) -> AssociationRead:
    association = await association_service.create_association(session, payload)
    return AssociationRead.model_validate(association)
