"""Configuración de la aplicación, cargada desde variables de entorno / .env."""

from functools import lru_cache
from typing import Any, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Aplicación -------------------------------------------------------
    PROJECT_NAME: str = "VehiRegistro API"
    DESCRIPTION: str = "Sistema de Fiscalización Municipal de Vehículos y Mototaxis"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["dev", "staging", "prod"] = "dev"

    # --- Seguridad --------------------------------------------------------
    SECRET_KEY: str = "dev-secret-key-no-usar-en-produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # jornada de fiscalización

    # --- Base de datos ----------------------------------------------------
    DATABASE_URL: str = "sqlite+aiosqlite:///./vehiregistro.db"
    SQL_ECHO: bool = False

    # --- CORS -------------------------------------------------------------
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # --- Archivos ---------------------------------------------------------
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 5
    ALLOWED_IMAGE_TYPES: set[str] = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    STATIC_URL_PATH: str = "/static/uploads"

    # --- Consulta vehicular externa (SUNARP) ------------------------------
    # Proveedor usado por el proxy Node original (legacy_proxy/server.js).
    # La placa se concatena al final de la URL: {SUNARP_API_URL}/{PLACA}
    SUNARP_API_URL: str = "https://api2.consultadatos.com/api/placa/leyenda"
    SUNARP_API_TOKEN: str = ""
    SUNARP_TIMEOUT_SECONDS: float = 10.0
    # Si el proveedor falla, responder con el catálogo simulado en vez de un error.
    SUNARP_FALLBACK_TO_MOCK: bool = True

    # --- Bootstrap --------------------------------------------------------
    SEED_ON_STARTUP: bool = True

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> Any:
        """Acepta 'a,b,c' además de una lista JSON."""
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "prod"

    @property
    def sunarp_enabled(self) -> bool:
        """Sin token no hay integración real: el servicio queda en modo mock."""
        return bool(self.SUNARP_API_TOKEN.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
