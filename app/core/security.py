"""Hashing de contraseñas (passlib/bcrypt) y emisión/validación de JWT."""

from datetime import datetime, timedelta, timezone
from typing import Any, Final

import jwt
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context: Final = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt sólo considera los primeros 72 bytes de la contraseña.
BCRYPT_MAX_BYTES: Final[int] = 72
TOKEN_TYPE_ACCESS: Final[str] = "access"


def hash_password(password: str) -> str:
    return pwd_context.hash(password[:BCRYPT_MAX_BYTES])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compara en tiempo constante; nunca propaga errores de formato del hash."""
    try:
        return pwd_context.verify(plain_password[:BCRYPT_MAX_BYTES], hashed_password)
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str | int,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, int]:
    """Devuelve (token, segundos_de_vigencia)."""
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    expire = now + delta

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": TOKEN_TYPE_ACCESS,
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, int(delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Devuelve el payload si el token es válido y del tipo esperado; si no, None."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except InvalidTokenError:
        return None

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        return None
    return payload
