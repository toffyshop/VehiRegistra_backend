"""Excepciones de dominio y manejadores globales con respuesta JSON uniforme.

Todo error responde con la misma forma:

    {
      "success": false,
      "error": {"code": "not_found", "message": "...", "details": [...]},
      "path": "/api/v1/vehicles/XYZ",
      "timestamp": "2026-07-20T12:00:00Z"
    }
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import logger


class AppException(Exception):
    """Base de todos los errores de negocio."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"
    message: str = "Ocurrió un error inesperado."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details
        self.headers = headers
        super().__init__(self.message)


class BadRequestError(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "bad_request"
    message = "La solicitud no es válida."


class UnauthorizedError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "unauthorized"
    message = "Credenciales inválidas o sesión expirada."

    def __init__(self, message: str | None = None, **kwargs: Any) -> None:
        kwargs.setdefault("headers", {"WWW-Authenticate": "Bearer"})
        super().__init__(message, **kwargs)


class ForbiddenError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "forbidden"
    message = "No tiene permisos para realizar esta acción."


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"
    message = "El recurso solicitado no existe."


class ConflictError(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"
    message = "El recurso ya existe o entra en conflicto con otro."


class UnprocessableError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "unprocessable_entity"
    message = "Los datos enviados no pudieron ser procesados."


class ExternalServiceError(AppException):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "external_service_error"
    message = "El servicio externo no está disponible."


def _error_body(
    request: Request,
    *,
    code: str,
    message: str,
    details: Any = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "success": False,
        "error": {"code": code, "message": message},
        "path": request.url.path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if details is not None:
        body["error"]["details"] = jsonable_encoder(details)
    return body


_LOCATIONS = frozenset({"body", "query", "path", "header", "cookie"})


def _field_name(loc: tuple[Any, ...]) -> str:
    """Nombre legible del campo que falló.

    FastAPI antepone la ubicación ('body', 'query', …); los errores que vienen
    de validar un modelo a mano no la traen, así que sólo se quita si está.
    """
    parts = loc[1:] if loc and loc[0] in _LOCATIONS else loc
    return ".".join(str(part) for part in parts) or "body"


def register_exception_handlers(app: FastAPI) -> None:
    """Registra los manejadores globales en la aplicación."""

    @app.exception_handler(AppException)
    async def _app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(
                request, code=exc.error_code, message=exc.message, details=exc.details
            ),
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": _field_name(err["loc"]),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                request,
                code="validation_error",
                message="Uno o más campos no superaron la validación.",
                details=details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = {
            status.HTTP_401_UNAUTHORIZED: "unauthorized",
            status.HTTP_403_FORBIDDEN: "forbidden",
            status.HTTP_404_NOT_FOUND: "not_found",
            status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
        }.get(exc.status_code, "http_error")
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(request, code=code, message=str(exc.detail)),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Violación de integridad en %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error_body(
                request,
                code="conflict",
                message="La operación viola una restricción de unicidad o integridad.",
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _sqlalchemy_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Error de base de datos en %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                request,
                code="database_error",
                message="Error al acceder a la base de datos.",
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Excepción no controlada en %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                request,
                code="internal_error",
                message="Ocurrió un error interno. Intente nuevamente.",
            ),
        )
