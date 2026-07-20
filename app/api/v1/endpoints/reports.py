"""Métricas globales del padrón vehicular."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ActiveUserDep, SessionDep
from app.schemas.dashboard import ReportStats
from app.services import dashboard_service

router = APIRouter()


@router.get(
    "/stats",
    response_model=ReportStats,
    summary="Estadísticas globales de fiscalización",
)
async def get_stats(
    session: SessionDep,
    current_user: ActiveUserDep,
    recientes: Annotated[
        int, Query(ge=1, le=50, description="Inspecciones recientes a incluir")
    ] = 5,
) -> ReportStats:
    """Totales por estado de permiso, desglose por asociación y por tipo de
    vehículo, más las últimas fiscalizaciones registradas."""
    return await dashboard_service.get_stats(session, recientes=recientes)
