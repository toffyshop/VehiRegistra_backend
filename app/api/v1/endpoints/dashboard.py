"""Resumen operativo de la pantalla principal."""

from fastapi import APIRouter

from app.api.deps import ActiveUserDep, SessionDep
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard_service

router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Indicadores del día y estado del sistema",
)
async def get_summary(
    session: SessionDep, current_user: ActiveUserDep
) -> DashboardSummary:
    """Inspecciones y registros de hoy, alertas activas, permisos por vencer
    y el estado de los servicios que consume la app."""
    return await dashboard_service.get_summary(session, current_user=current_user)
