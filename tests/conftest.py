"""Configuración común de las pruebas.

Cada prueba corre contra una base SQLite **en memoria** propia, sin tocar
`vehiregistro.db` ni el seed de arranque. La autenticación se sustituye por un
fiscalizador de prueba para que los tests midan la lógica de negocio y no el
flujo de login (que tiene sus propias pruebas).
"""

import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import SessionDep, get_current_active_user
from app.core.database import get_session
from app.main import app
from app.models import Base
from app.models.enums import EstadoPermiso
from app.models.user import User
from app.models.vehicle import Vehicle

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def session_factory() -> AsyncGenerator[async_sessionmaker[AsyncSession], None]:
    """Motor en memoria compartido por todas las conexiones de la prueba.

    `StaticPool` es imprescindible: sin él cada conexión abriría su propia base
    vacía y las tablas creadas aquí no serían visibles desde la API.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    await engine.dispose()


@pytest_asyncio.fixture
async def fiscalizador(
    session_factory: async_sessionmaker[AsyncSession],
) -> User:
    async with session_factory() as session:
        user = User(
            dni="12345678",
            email="prueba@municipalidad.gob.pe",
            code="FISC-TEST",
            full_name="FISCALIZADOR DE PRUEBA",
            hashed_password="no-se-usa-en-estas-pruebas",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession], fiscalizador: User
) -> AsyncGenerator[AsyncClient, None]:
    async def _get_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    async def _usuario_actual(session: SessionDep) -> User:
        """El usuario debe venir de la sesión del request.

        Devolver la instancia del fixture la dejaría desligada de esa sesión y
        cualquier `session.refresh()` fallaría.
        """
        return await session.get(User, fiscalizador.id)

    app.dependency_overrides[get_session] = _get_session
    app.dependency_overrides[get_current_active_user] = _usuario_actual

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def padron(
    session_factory: async_sessionmaker[AsyncSession], fiscalizador: User
) -> list[Vehicle]:
    """Tres vehículos con datos deliberadamente distintos entre sí."""
    vehiculos = [
        Vehicle(
            placa="A3H-451",
            propietario_nombre="JUAN CARLOS QUISPE MAMANI",
            propietario_dni="45781203",
            marca_modelo="BAJAJ RE 205 4T",
            estado_permiso=EstadoPermiso.VIGENTE,
            alerta_robo=False,
        ),
        Vehicle(
            placa="M2K-889",
            propietario_nombre="MARIA ELENA CONDORI APAZA",
            propietario_dni="42310998",
            marca_modelo="HONDA CG 125 CARGO",
            estado_permiso=EstadoPermiso.VENCIDO,
            alerta_robo=False,
        ),
        Vehicle(
            placa="V7B-233",
            propietario_nombre="PEDRO ALBERTO HUAMAN ROJAS",
            propietario_dni="40889123",
            marca_modelo="TOYOTA YARIS 1.3",
            estado_permiso=EstadoPermiso.EN_TRAMITE,
            alerta_robo=True,
        ),
    ]
    async with session_factory() as session:
        for vehiculo in vehiculos:
            vehiculo.codigo_qr = uuid.uuid4().hex
            vehiculo.created_by_user_id = fiscalizador.id
            session.add(vehiculo)
        await session.commit()
        for vehiculo in vehiculos:
            await session.refresh(vehiculo)
    return vehiculos
