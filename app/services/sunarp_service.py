"""Servicio de consulta vehicular externa (SUNARP).

Tiene dos modos, elegidos automáticamente según la configuración:

* **Real** — cuando hay `SUNARP_API_TOKEN`. Consulta por HTTP al proveedor
  configurado en `SUNARP_API_URL` (el mismo que usaba el proxy Node de
  `legacy_proxy/server.js`: `Authorization: Bearer <token>`).
* **Mock** — sin token. Devuelve datos precargados y, para placas fuera del
  catálogo, un registro derivado del hash de la placa (misma entrada → misma
  salida). Permite demostrar la app sin depender del proveedor.

Si el proveedor real falla y `SUNARP_FALLBACK_TO_MOCK` está activo, se responde
con el mock para no bloquear el registro en campo; el campo `source` de la
respuesta indica siempre de dónde salió el dato (`"sunarp"` o `"mock"`).
"""

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import logger
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


# --- Integración con el proveedor real -----------------------------------

# Nombres alternativos con los que el proveedor puede exponer cada dato. Se
# prueban en orden; el mapeo es tolerante porque el contrato exacto todavía no
# está documentado (falta el token para inspeccionar una respuesta real).
_CAMPOS: dict[str, tuple[str, ...]] = {
    "marca": ("marca", "brand", "vehiculo_marca"),
    "modelo": ("modelo", "model", "vehiculo_modelo"),
    "anio": ("anio", "año", "anno", "year", "anio_fabricacion", "modelo_anio"),
    "color": ("color", "colour"),
    "nro_motor": ("nro_motor", "numero_motor", "motor", "engine"),
    "nro_serie": ("nro_serie", "numero_serie", "serie", "vin", "chasis"),
    "categoria": ("categoria", "category", "clase", "tipo"),
    "estado_registral": ("estado_registral", "estado", "situacion", "status"),
}
_CAMPOS_PROPIETARIO: dict[str, tuple[str, ...]] = {
    "nombre_completo": ("nombre_completo", "propietario", "titular", "nombre", "owner"),
    "dni": ("dni", "documento", "nro_documento", "num_documento"),
    "direccion": ("direccion", "domicilio", "address"),
}


def _aplanar(payload: Any) -> dict[str, Any]:
    """Desenvuelve `{"data": {...}}` / `{"result": {...}}` y aplana un nivel.

    Deja las claves en minúsculas para poder buscarlas sin importar cómo las
    escriba el proveedor.
    """
    if not isinstance(payload, dict):
        return {}

    for envoltura in ("data", "result", "resultado", "vehiculo"):
        interno = payload.get(envoltura)
        if isinstance(interno, dict):
            payload = {**payload, **interno}
        elif isinstance(interno, list) and interno and isinstance(interno[0], dict):
            payload = {**payload, **interno[0]}

    plano: dict[str, Any] = {}
    for clave, valor in payload.items():
        clave_norm = str(clave).strip().lower()
        if isinstance(valor, dict):
            # Un nivel anidado (p. ej. {"propietario": {"nombre": ...}}).
            plano[clave_norm] = valor
            for sub_clave, sub_valor in valor.items():
                plano.setdefault(str(sub_clave).strip().lower(), sub_valor)
        else:
            plano[clave_norm] = valor
    return plano


def _primero(plano: dict[str, Any], claves: tuple[str, ...]) -> Any:
    """Primer valor escalar no vacío entre las claves candidatas.

    Se descartan dicts y listas: una clave como "propietario" puede contener el
    objeto anidado en vez del nombre, y ese objeto no es el valor buscado.
    """
    for clave in claves:
        valor = plano.get(clave)
        if isinstance(valor, dict | list):
            continue
        if valor not in (None, ""):
            return valor
    return None


def _mapear_respuesta(payload: Any) -> dict | None:
    """Traduce la respuesta del proveedor al formato interno.

    Devuelve `None` si no se reconoce ni la marca ni el modelo: sin eso la
    respuesta no sirve para autocompletar el formulario.
    """
    plano = _aplanar(payload)
    if not plano:
        return None

    marca = _primero(plano, _CAMPOS["marca"])
    modelo = _primero(plano, _CAMPOS["modelo"])
    if marca is None and modelo is None:
        return None

    anio = _primero(plano, _CAMPOS["anio"])
    try:
        anio = int(str(anio)[:4]) if anio is not None else None
    except (TypeError, ValueError):
        anio = None

    propietario_plano = plano
    anidado = plano.get("propietario") or plano.get("titular")
    if isinstance(anidado, dict):
        propietario_plano = {
            **plano,
            **{str(k).strip().lower(): v for k, v in anidado.items()},
        }

    record: dict[str, Any] = {
        "marca": str(marca or "").upper() or "NO DISPONIBLE",
        "modelo": str(modelo or "").upper() or "NO DISPONIBLE",
        "anio": anio,
        "propietario": {
            # El proveedor puede no devolver datos del titular: en ese caso el
            # fiscalizador los completa a mano en el formulario.
            "nombre_completo": str(
                _primero(propietario_plano, _CAMPOS_PROPIETARIO["nombre_completo"])
                or "NO DISPONIBLE"
            ).upper(),
            "dni": str(_primero(propietario_plano, _CAMPOS_PROPIETARIO["dni"]) or ""),
            "direccion": _primero(
                propietario_plano, _CAMPOS_PROPIETARIO["direccion"]
            ),
        },
        # El proveedor de placas no expone alertas de robo: se marca en el padrón.
        "alerta_robo": bool(_primero(plano, ("alerta_robo", "robo", "requisitoria"))),
    }

    for campo in ("color", "nro_motor", "nro_serie", "categoria", "estado_registral"):
        valor = _primero(plano, _CAMPOS[campo])
        record[campo] = str(valor).upper() if valor is not None else None

    return record


async def _consultar_proveedor(placa: str) -> dict | None:
    """Consulta HTTP al proveedor. Devuelve `None` ante cualquier fallo."""
    url = f"{settings.SUNARP_API_URL.rstrip('/')}/{placa}"
    try:
        async with httpx.AsyncClient(timeout=settings.SUNARP_TIMEOUT_SECONDS) as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {settings.SUNARP_API_TOKEN}",
                    "Accept": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                },
            )
            response.raise_for_status()
            record = _mapear_respuesta(response.json())
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "El proveedor respondió %s para la placa %s.",
            exc.response.status_code,
            placa,
        )
        return None
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("No se pudo consultar la placa %s: %s", placa, exc)
        return None

    if record is None:
        logger.warning(
            "La respuesta del proveedor para %s no trae marca ni modelo.", placa
        )
    return record


async def _fetch_external(placa: str) -> tuple[dict, str]:
    """Resuelve la placa contra el proveedor real o contra el catálogo mock."""
    if settings.sunarp_enabled:
        record = await _consultar_proveedor(placa)
        if record is not None:
            return record, "sunarp"
        if not settings.SUNARP_FALLBACK_TO_MOCK:
            raise NotFoundError(
                "El servicio de consulta vehicular no está disponible en este momento.",
                details={"placa": placa},
            )
        logger.info("Se responde con el catálogo simulado para la placa %s.", placa)

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
