"""Punto de entrada de la API VehiRegistro."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import dispose_engine, init_models
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Iniciando %s (%s)", settings.PROJECT_NAME, settings.ENVIRONMENT)

    # await init_models()  # <- Reemplazado por migraciones Alembic
    if settings.SEED_ON_STARTUP and not settings.is_production:
        from app.db.seed import seed_database

        await seed_database()

    yield

    await dispose_engine()
    logger.info("Aplicación detenida correctamente.")


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # Sirve las fotografías subidas.
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.STATIC_URL_PATH,
        StaticFiles(directory=upload_dir),
        name="uploads",
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["Sistema"], summary="Información de la API")
    async def root() -> dict[str, str]:
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
            "api": settings.API_V1_PREFIX,
        }

    @app.get("/health", tags=["Sistema"], summary="Health check")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "environment": settings.ENVIRONMENT,
            "time": datetime.now(timezone.utc).isoformat(),
        }

    return app


app = create_application()
