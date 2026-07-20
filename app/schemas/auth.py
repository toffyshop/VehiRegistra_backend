"""Schemas de autenticación."""

from pydantic import BaseModel, Field

from app.schemas.user import UserRead


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Vigencia del token en segundos")
    user: UserRead


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int
    type: str


class LoginRequest(BaseModel):
    """Alternativa JSON al form-data de OAuth2 (útil desde el cliente móvil)."""

    username: str = Field(..., description="DNI, código de fiscalizador o email")
    password: str = Field(..., min_length=1)
