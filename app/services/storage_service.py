"""Almacenamiento de las fotografías de los vehículos.

Guarda en disco local bajo `settings.UPLOAD_DIR`. Para producción bastaría con
reimplementar `save_vehicle_photo` contra S3/Azure Blob manteniendo la firma.
"""

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BadRequestError
from app.core.logging import logger

_EXTENSION_BY_TYPE: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
_CHUNK_SIZE = 1024 * 1024  # 1 MB


def _upload_root() -> Path:
    root = Path(settings.UPLOAD_DIR) / "vehicles"
    root.mkdir(parents=True, exist_ok=True)
    return root


async def save_vehicle_photo(file: UploadFile, *, placa: str) -> str:
    """Persiste la imagen y devuelve la URL pública absoluta.

    Valida el content-type y corta la escritura si se excede el tamaño máximo,
    de modo que un archivo enorme nunca llega a ocupar disco por completo.
    """
    content_type = (file.content_type or "").lower()
    if content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise BadRequestError(
            "Formato de imagen no permitido. Use JPEG, PNG o WEBP.",
            details={"content_type_recibido": content_type or None},
        )

    extension = _EXTENSION_BY_TYPE[content_type]
    filename = f"{placa.replace('-', '')}_{uuid.uuid4().hex[:12]}{extension}"
    destination = _upload_root() / filename

    written = 0
    try:
        with destination.open("wb") as buffer:
            while chunk := await file.read(_CHUNK_SIZE):
                written += len(chunk)
                if written > settings.max_upload_size_bytes:
                    raise BadRequestError(
                        f"La imagen supera el tamaño máximo de "
                        f"{settings.MAX_UPLOAD_SIZE_MB} MB."
                    )
                buffer.write(chunk)
    except BadRequestError:
        destination.unlink(missing_ok=True)
        raise
    except OSError as exc:
        destination.unlink(missing_ok=True)
        logger.exception("No se pudo guardar la fotografía de %s", placa)
        raise BadRequestError("No fue posible almacenar la fotografía.") from exc
    finally:
        await file.close()

    if written == 0:
        destination.unlink(missing_ok=True)
        raise BadRequestError("El archivo de imagen está vacío.")

    return f"{settings.PUBLIC_BASE_URL.rstrip('/')}{settings.STATIC_URL_PATH}/vehicles/{filename}"


def delete_photo(photo_url: str | None) -> None:
    """Elimina el archivo asociado a una URL previamente generada."""
    if not photo_url:
        return
    filename = photo_url.rsplit("/", 1)[-1]
    (_upload_root() / filename).unlink(missing_ok=True)
