"""Agregador de routers de la v1."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    associations,
    auth,
    dashboard,
    external,
    inspections,
    reports,
    users,
    vehicles,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reportes"])
api_router.include_router(external.router, prefix="/external", tags=["Integración SUNARP"])
api_router.include_router(vehicles.router, prefix="/vehicles", tags=["Vehículos"])
api_router.include_router(
    inspections.router, prefix="/inspections", tags=["Fiscalizaciones"]
)
api_router.include_router(
    associations.router, prefix="/associations", tags=["Asociaciones"]
)
