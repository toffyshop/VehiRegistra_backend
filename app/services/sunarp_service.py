"""Servicio de consulta vehicular externa (SUNARP) — implementación mock.

Devuelve datos precargados para autocompletar el formulario de registro. Las
placas no incluidas en el catálogo se generan de forma determinista a partir de
la propia placa (misma entrada → misma salida), lo que permite demostrar la app
sin depender de la disponibilidad del servicio real.

Para conectar el servicio real: reemplazar el cuerpo de `_fetch_external` por la
llamada HTTP (httpx.AsyncClient) hacia el proveedor y mapear su respuesta a
`SunarpVehicleData`. El proxy Node existente (`VehiRegistra_backend/server.js`)
ya consulta ese proveedor y sirve como referencia del formato.
"""

from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.vehicle import Vehicle
from app.schemas.sunarp import SunarpOwner, SunarpResponse, SunarpVehicleData
from app.schemas.vehicle import normalize_placa

# --- Catálogo precargado -------------------------------------------------

_MOCK_DB: dict[str, dict] = {
    "A3H-451": {
        "marca": "BAJAJ",
        "modelo": "RE 205 4T",
        "anio": 2021,
        "color": "AZUL",
        "nro_motor": "AEMBTG12345",
        "nro_serie": "MD2A11CZ7MWA12345",
        "categoria": "L5",
        "estado_registral": "INSCRITO",
        "propietario": {
            "nombre_completo": "JUAN CARLOS QUISPE MAMANI",
            "dni": "45781203",
            "direccion": "AV. LOS ANDES 452 - JULIACA",
        },
        "alerta_robo": False,
    },
    "M2K-889": {
        "marca": "HONDA",
        "modelo": "CG 125 CARGO",
        "anio": 2019,
        "color": "ROJO",
        "nro_motor": "JC30E9012233",
        "nro_serie": "9C2JC3010KR012233",
        "categoria": "L5",
        "estado_registral": "INSCRITO",
        "propietario": {
            "nombre_completo": "MARIA ELENA CONDORI APAZA",
            "dni": "42310998",
            "direccion": "JR. HUANCANE 118 - JULIACA",
        },
        "alerta_robo": False,
    },
    "V7B-233": {
        "marca": "TOYOTA",
        "modelo": "YARIS 1.3",
        "anio": 2018,
        "color": "PLATA",
        "nro_motor": "2NZ7745512",
        "nro_serie": "JTDBT923781234567",
        "categoria": "M1",
        "estado_registral": "INSCRITO",
        "propietario": {
            "nombre_completo": "PEDRO ALBERTO HUAMAN ROJAS",
            "dni": "40889123",
            "direccion": "URB. SANTA MARIA C-12 - JULIACA",
        },
        "alerta_robo": True,
    },
}

# --- Generación determinista para placas fuera del catálogo --------------

_MARCAS: list[tuple[str, str, str]] = [
    ("BAJAJ", "RE 205 4T", "L5"),
    ("HONDA", "CG 125 CARGO", "L5"),
    ("TVS", "KING DELUXE", "L5"),
    ("WANXIN", "WX 200 ZH", "L5"),
    ("TOYOTA", "YARIS 1.3", "M1"),
    ("NISSAN", "SENTRA B13", "M1"),
]
_COLORES = ["AZUL", "ROJO", "NEGRO", "BLANCO", "PLATA", "VERDE", "AMARILLO"]
_NOMBRES = ["LUIS", "ANA", "JOSE", "ROSA", "MIGUEL", "CARMEN", "VICTOR", "SONIA"]
_APELLIDOS = ["QUISPE", "MAMANI", "CONDORI", "APAZA", "CHOQUE", "TICONA", "HUANCA"]


def _deterministic_record(placa: str) -> dict:
    """Deriva datos estables desde el hash de la placa."""
    digest = sha256(placa.encode()).digest()

    marca, modelo, categoria = _MARCAS[digest[0] % len(_MARCAS)]
    nombre = (
        f"{_NOMBRES[digest[3] % len(_NOMBRES)]} "
        f"{_APELLIDOS[digest[4] % len(_APELLIDOS)]} "
        f"{_APELLIDOS[digest[5] % len(_APELLIDOS)]}"
    )
    dni = f"{40_000_000 + int.from_bytes(digest[6:10], 'big') % 10_000_000}"

    return {
        "marca": marca,
        "modelo": modelo,
        "anio": 2015 + digest[1] % 11,
        "color": _COLORES[digest[2] % len(_COLORES)],
        "nro_motor": f"{placa.replace('-', '')}{digest[11]:03d}MT",
        "nro_serie": f"9C2{digest.hex()[:14].upper()}",
        "categoria": categoria,
        "estado_registral": "INSCRITO",
        "propietario": {
            "nombre_completo": nombre,
            "dni": dni,
            "direccion": f"JR. LOS PINOS {100 + digest[12]} - JULIACA",
        },
        # ~6 % de las placas generadas simulan una alerta de robo.
        "alerta_robo": digest[13] % 16 == 0,
    }


async def _fetch_external(placa: str) -> tuple[dict, str]:
    """Punto de integración. Hoy resuelve contra el catálogo mock."""
    if placa in _MOCK_DB:
        return _MOCK_DB[placa], "mock"
    return _deterministic_record(placa), "mock"


async def consultar_placa(session: AsyncSession, placa: str) -> SunarpResponse:
    """Consulta los datos de una placa para autocompletar el registro."""
    try:
        normalized = normalize_placa(placa)
    except ValueError as exc:
        # Traducimos el error de formato a un 404 semántico del recurso externo.
        raise NotFoundError(str(exc)) from exc

    record, source = await _fetch_external(normalized)

    ya_registrado = bool(
        await session.scalar(select(Vehicle.id).where(Vehicle.placa == normalized))
    )

    data = SunarpVehicleData(
        placa=normalized,
        marca=record["marca"],
        modelo=record["modelo"],
        marca_modelo=f"{record['marca']} {record['modelo']}",
        anio=record.get("anio"),
        color=record.get("color"),
        nro_motor=record.get("nro_motor"),
        nro_serie=record.get("nro_serie"),
        categoria=record.get("categoria"),
        estado_registral=record.get("estado_registral"),
        propietario=SunarpOwner(**record["propietario"]),
        alerta_robo=record.get("alerta_robo", False),
    )

    return SunarpResponse(
        success=True,
        source=source,
        consulted_at=datetime.now(timezone.utc),
        ya_registrado=ya_registrado,
        data=data,
    )
