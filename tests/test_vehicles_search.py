"""Filtros y búsqueda de GET /api/v1/vehicles.

Es la pantalla más usada de la app (consulta en campo), así que se cubren los
tres caminos que el fiscalizador usa de verdad: buscar por placa, por DNI del
propietario y filtrar por estado del permiso.
"""

import pytest
from httpx import AsyncClient

from app.models.vehicle import Vehicle

RUTA = "/api/v1/vehicles"

pytestmark = pytest.mark.asyncio


async def test_lista_completa(client: AsyncClient, padron: list[Vehicle]) -> None:
    response = await client.get(RUTA)

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["meta"]["total"] == 3
    assert len(cuerpo["items"]) == 3


@pytest.mark.parametrize(
    "termino",
    ["A3H-451", "a3h-451", "A3H", "451"],
    ids=["exacta", "minusculas", "prefijo", "sufijo"],
)
async def test_busqueda_por_placa(
    client: AsyncClient, padron: list[Vehicle], termino: str
) -> None:
    """La búsqueda es parcial e insensible a mayúsculas."""
    response = await client.get(RUTA, params={"search": termino})

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["placa"] for item in items] == ["A3H-451"]


async def test_busqueda_por_dni(client: AsyncClient, padron: list[Vehicle]) -> None:
    response = await client.get(RUTA, params={"search": "42310998"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["placa"] == "M2K-889"
    assert items[0]["propietario_dni"] == "42310998"


async def test_busqueda_por_nombre_del_propietario(
    client: AsyncClient, padron: list[Vehicle]
) -> None:
    response = await client.get(RUTA, params={"search": "condori"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["placa"] for item in items] == ["M2K-889"]


async def test_busqueda_por_marca(client: AsyncClient, padron: list[Vehicle]) -> None:
    response = await client.get(RUTA, params={"search": "toyota"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["placa"] for item in items] == ["V7B-233"]


async def test_busqueda_sin_coincidencias(
    client: AsyncClient, padron: list[Vehicle]
) -> None:
    response = await client.get(RUTA, params={"search": "ZZZ-999"})

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["items"] == []
    assert cuerpo["meta"]["total"] == 0


async def test_filtro_por_estado(client: AsyncClient, padron: list[Vehicle]) -> None:
    response = await client.get(RUTA, params={"estado": "VIGENTE"})

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["placa"] for item in items] == ["A3H-451"]


async def test_filtro_solo_alertas(client: AsyncClient, padron: list[Vehicle]) -> None:
    response = await client.get(RUTA, params={"solo_alertas": True})

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["placa"] for item in items] == ["V7B-233"]


async def test_filtros_combinados_se_intersecan(
    client: AsyncClient, padron: list[Vehicle]
) -> None:
    """VIGENTE + un término que sólo casa con otro vehículo no devuelve nada."""
    response = await client.get(
        RUTA, params={"estado": "VIGENTE", "search": "toyota"}
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_paginacion(client: AsyncClient, padron: list[Vehicle]) -> None:
    response = await client.get(RUTA, params={"page": 1, "size": 2})

    assert response.status_code == 200
    meta = response.json()["meta"]
    assert len(response.json()["items"]) == 2
    assert meta["total"] == 3
    assert meta["pages"] == 2
    assert meta["has_next"] is True
    assert meta["has_prev"] is False
