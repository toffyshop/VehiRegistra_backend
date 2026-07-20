"""Logger único de la aplicación."""

import logging
import sys

from app.core.config import settings


def _build_logger() -> logging.Logger:
    log = logging.getLogger("vehiregistro")
    if log.handlers:  # evita duplicar handlers con el reload de uvicorn
        return log

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    log.addHandler(handler)
    log.setLevel(logging.INFO if settings.is_production else logging.DEBUG)
    log.propagate = False
    return log


logger: logging.Logger = _build_logger()
