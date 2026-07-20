"""Schemas de autenticación."""

from pydantic import BaseModel, EmailStr, Field

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
    """Alternativa JSON al form-data de OAuth2 (útil desde el cliente móvil).

    A diferencia de `/auth/login`, que sigue el estándar OAuth2 y recibe el
    campo `username`, aquí se inicia sesión con el correo electrónico.
    """

    email: EmailStr = Field(..., description="Correo institucional del fiscalizador")
    password: str = Field(..., min_length=1)
