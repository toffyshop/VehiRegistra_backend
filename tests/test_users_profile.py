"""Perfil del fiscalizador tras el rediseño de la pantalla.

El diseño final retiró "cambiar contraseña" y el campo celular de la edición
de perfil; estas pruebas evitan que vuelvan a aparecer por descuido.
"""

import pytest
from httpx import AsyncClient

from app.models.user import User

pytestmark = pytest.mark.asyncio


async def test_perfil_incluye_metricas(
    client: AsyncClient, fiscalizador: User
) -> None:
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["code"] == "FISC-TEST"
    assert set(cuerpo["metrics"]) == {
        "total_registros",
        "total_fiscalizaciones",
        "registros_mes_actual",
    }


async def test_no_existe_endpoint_de_cambio_de_contrasena(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/users/me/change-password",
        json={
            "current_password": "loquesea",
            "new_password": "otracosa123",
            "confirm_password": "otracosa123",
        },
    )

    assert response.status_code == 404  # la ruta ya no está registrada


async def test_editar_perfil_actualiza_campos_permitidos(
    client: AsyncClient, fiscalizador: User
) -> None:
    response = await client.put(
        "/api/v1/users/me", json={"full_name": "NUEVO NOMBRE COMPLETO"}
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "NUEVO NOMBRE COMPLETO"


async def test_editar_perfil_ignora_el_celular(
    client: AsyncClient, fiscalizador: User
) -> None:
    """Un cliente antiguo que siga enviando `phone` no debe modificarlo."""
    original = fiscalizador.phone

    response = await client.put(
        "/api/v1/users/me",
        json={"full_name": "NOMBRE ACTUALIZADO", "phone": "999888777"},
    )

    assert response.status_code == 200
    assert response.json()["phone"] == original
