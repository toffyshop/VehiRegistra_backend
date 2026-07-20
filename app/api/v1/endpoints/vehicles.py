"""Padrón de vehículos y mototaxis."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Path, Query, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.api.deps import ActiveUserDep, PaginationDep, SessionDep
from app.models.enums import EstadoPermiso
from app.schemas.common import ErrorResponse, Page
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleDetail,
    VehicleRead,
    VehicleRenew,
    VehicleUpdate,
)
from app.services import storage_service, vehicle_service

router = APIRouter()


def _clean(value: str | None) -> str | None:
    """Un campo de texto vacío en un formulario equivale a 'no enviado'.

    Los clientes móviles envían "" para los campos opcionales que el
    fiscalizador dejó en blanco; sin esto, Pydantic los rechazaría.
    """
    if value is None:
        return None
    value = value.strip()
    return value or None


def vehicle_create_form(
    placa: Annotated[str, Form(description="Ej. A3H-451 o A3H451")],
    propietario_nombre: Annotated[str, Form()],
    propietario_dni: Annotated[str, Form(description="8 dígitos")],
    marca_modelo: Annotated[str, Form()],
    nro_motor: Annotated[str | None, Form()] = None,
    asociacion_id: Annotated[str | None, Form()] = None,
    anio: Annotated[str | None, Form()] = None,
    color: Annotated[str | None, Form()] = None,
    estado_permiso: Annotated[EstadoPermiso, Form()] = EstadoPermiso.EN_TRAMITE,
    fecha_emision: Annotated[str | None, Form(description="YYYY-MM-DD")] = None,
    fecha_vencimiento: Annotated[str | None, Form(description="YYYY-MM-DD")] = None,
    en_circulacion: Annotated[bool, Form()] = True,
    alerta_robo: Annotated[bool, Form()] = False,
) -> VehicleCreate:
    """Convierte el `multipart/form-data` en el schema validado.

    La validación real sigue viviendo en `VehicleCreate`: aquí sólo se adapta
    el transporte y se traducen los errores al formato 422 de la API.
    """
    raw: dict[str, Any] = {
        "placa": placa,
        "propietario_nombre": propietario_nombre,
        "propietario_dni": propietario_dni,
        "marca_modelo": marca_modelo,
        "nro_motor": _clean(nro_motor),
        "asociacion_id": _clean(asociacion_id),
        "anio": _clean(anio),
        "color": _clean(color),
        "estado_permiso": estado_permiso,
        "fecha_emision": _clean(fecha_emision),
        "fecha_vencimiento": _clean(fecha_vencimiento),
        "en_circulacion": en_circulacion,
        "alerta_robo": alerta_robo,
    }
    try:
        return VehicleCreate.model_validate(raw)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


VehicleFormDep = Annotated[VehicleCreate, Depends(vehicle_create_form)]


@router.post(
    "",
    response_model=VehicleDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un vehículo o mototaxi",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse, "description": "Fotografía inválida o muy pesada"
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse, "description": "La asociación indicada no existe"
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse, "description": "La placa ya está registrada"
        },
    },
)
async def create_vehicle(
    session: SessionDep,
    current_user: ActiveUserDep,
    payload: VehicleFormDep,
    photo: Annotated[
        UploadFile | None, File(description="Fotografía del vehículo (JPEG/PNG/WEBP)")
    ] = None,
) -> VehicleDetail:
    """Alta en el padrón, enviada como `multipart/form-data`.

    La imagen se valida y almacena **antes** de insertar el registro, de modo
    que un archivo rechazado no deje un vehículo sin fotografía en la base.
    """
    photo_url: str | None = None
    if photo is not None and photo.filename:
        photo_url = await storage_service.save_vehicle_photo(photo, placa=payload.placa)

    try:
        vehicle = await vehicle_service.create_vehicle(
            session, payload, current_user=current_user, photo_url=photo_url
        )
    except Exception:
        # Si el insert falla, no dejamos el archivo huérfano en disco.
        storage_service.delete_photo(photo_url)
        raise

    vehicle = await vehicle_service.get_by_id(session, vehicle.id)
    return await vehicle_service.to_detail(session, vehicle)


@router.get(
    "",
    response_model=Page[VehicleRead],
    summary="Listar vehículos con paginación, filtro y búsqueda",
)
async def list_vehicles(
    session: SessionDep,
    current_user: ActiveUserDep,
    pagination: PaginationDep,
    estado: Annotated[
        EstadoPermiso | None, Query(description="Filtrar por estado del permiso")
    ] = None,
    search: Annotated[
        str | None,
        Query(min_length=1, max_length=100, description="Placa, DNI, propietario o marca"),
    ] = None,
    asociacion_id: Annotated[int | None, Query(ge=1)] = None,
    solo_alertas: Annotated[
        bool, Query(description="Sólo vehículos con alerta de robo")
    ] = False,
) -> Page[VehicleRead]:
    """Resultados ordenados del más reciente al más antiguo."""
    vehicles, total = await vehicle_service.list_vehicles(
        session,
        page=pagination.page,
        size=pagination.size,
        estado=estado,
        search=search,
        asociacion_id=asociacion_id,
        solo_alertas=solo_alertas,
    )
    return Page[VehicleRead].create(
        [VehicleRead.model_validate(v) for v in vehicles],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


@router.get(
    "/{placa}",
    response_model=VehicleDetail,
    summary="Detalle por placa o código QR",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse, "description": "Vehículo no encontrado"
        },
    },
)
async def get_vehicle(
    session: SessionDep,
    current_user: ActiveUserDep,
    placa: Annotated[
        str,
        Path(
            min_length=6,
            max_length=40,
            description="Placa (A3H-451 o A3H451) o código impreso en el QR",
        ),
    ],
) -> VehicleDetail:
    vehicle = await vehicle_service.get_by_placa_o_qr(session, placa)
    return await vehicle_service.to_detail(session, vehicle)


@router.put(
    "/{vehicle_id}",
    response_model=VehicleDetail,
    summary="Actualizar los datos de un vehículo",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse, "description": "Vehículo o asociación inexistente"
        },
    },
)
async def update_vehicle(
    session: SessionDep,
    current_user: ActiveUserDep,
    payload: VehicleUpdate,
    vehicle_id: Annotated[int, Path(ge=1)],
) -> VehicleDetail:
    """Actualización parcial: sólo se tocan los campos presentes en el cuerpo."""
    vehicle = await vehicle_service.update_vehicle(session, vehicle_id, payload)
    return await vehicle_service.to_detail(session, vehicle)


@router.put(
    "/{vehicle_id}/renew",
    response_model=VehicleDetail,
    summary="Renovar el permiso de circulación",
    responses={
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "La fecha de vencimiento no es posterior a hoy",
        },
    },
)
async def renew_permit(
    session: SessionDep,
    current_user: ActiveUserDep,
    payload: VehicleRenew,
    vehicle_id: Annotated[int, Path(ge=1)],
) -> VehicleDetail:
    """Fija la nueva vigencia y deja el vehículo en estado `VIGENTE`."""
    vehicle = await vehicle_service.renew_permit(session, vehicle_id, payload)
    return await vehicle_service.to_detail(session, vehicle)


@router.put(
    "/{vehicle_id}/photo",
    response_model=VehicleDetail,
    summary="Reemplazar la fotografía del vehículo",
)
async def update_photo(
    session: SessionDep,
    current_user: ActiveUserDep,
    vehicle_id: Annotated[int, Path(ge=1)],
    photo: Annotated[UploadFile, File(description="Nueva fotografía")],
) -> VehicleDetail:
    vehicle = await vehicle_service.get_by_id(session, vehicle_id)
    anterior = vehicle.photo_url

    photo_url = await storage_service.save_vehicle_photo(photo, placa=vehicle.placa)
    vehicle = await vehicle_service.set_photo(session, vehicle, photo_url)
    storage_service.delete_photo(anterior)

    vehicle = await vehicle_service.get_by_id(session, vehicle_id)
    return await vehicle_service.to_detail(session, vehicle)
