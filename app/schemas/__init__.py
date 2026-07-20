"""Schemas Pydantic v2 (contratos de entrada/salida de la API)."""

from app.schemas.association import AssociationCreate, AssociationRead
from app.schemas.auth import LoginRequest, Token, TokenPayload
from app.schemas.common import ErrorResponse, Message, Page, PageMeta
from app.schemas.dashboard import DashboardSummary, ReportStats, SystemStatus
from app.schemas.inspection import InspectionCreate, InspectionRead
from app.schemas.sunarp import SunarpResponse, SunarpVehicleData
from app.schemas.user import (
    ChangePasswordRequest,
    UserCreate,
    UserMetrics,
    UserProfile,
    UserRead,
    UserUpdate,
)
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleDetail,
    VehicleRead,
    VehicleRenew,
    VehicleUpdate,
)

__all__ = [
    "AssociationCreate",
    "AssociationRead",
    "ChangePasswordRequest",
    "DashboardSummary",
    "ErrorResponse",
    "InspectionCreate",
    "InspectionRead",
    "LoginRequest",
    "Message",
    "Page",
    "PageMeta",
    "ReportStats",
    "SunarpResponse",
    "SunarpVehicleData",
    "SystemStatus",
    "Token",
    "TokenPayload",
    "UserCreate",
    "UserMetrics",
    "UserProfile",
    "UserRead",
    "UserUpdate",
    "VehicleCreate",
    "VehicleDetail",
    "VehicleRead",
    "VehicleRenew",
    "VehicleUpdate",
]
