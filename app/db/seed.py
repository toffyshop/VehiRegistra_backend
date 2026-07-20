"""Datos iniciales para desarrollo y demostración.

Es idempotente: si ya existe algún fiscalizador, no hace nada.

Ejecutable de forma independiente:

    python -m app.db.seed
"""

import asyncio
import uuid
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, init_models
from app.core.logging import logger
from app.core.security import hash_password
from app.models.association import Association
from app.models.base import today, utcnow
from app.models.enums import EstadoPermiso, EstadoResultado, TipoVehiculo
from app.models.inspection import Inspection
from app.models.user import User
from app.models.vehicle import Vehicle

DEMO_PASSWORD = "Fiscal2026!"


async def _seed(session: AsyncSession) -> None:
    ya_poblada = await session.scalar(select(func.count(User.id)))
    if ya_poblada:
        logger.info("La base ya contiene datos; se omite el seed.")
        return

    logger.info("Poblando base de datos con datos de demostración…")

    fiscalizadores = [
        User(
            dni="70112233",
            email="j.ramirez@muni.gob.pe",
            phone="951234567",
            code="FIS-001",
            area="Gerencia de Transportes",
            full_name="JORGE RAMIREZ SALAS",
            hashed_password=hash_password(DEMO_PASSWORD),
        ),
        User(
            dni="70445566",
            email="l.torres@muni.gob.pe",
            phone="962345678",
            code="FIS-002",
            area="Fiscalización de Tránsito",
            full_name="LUCIA TORRES VILCA",
            hashed_password=hash_password(DEMO_PASSWORD),
        ),
    ]
    session.add_all(fiscalizadores)
    await session.flush()

    asociaciones = [
        Association(nombre="ASOC. SEÑOR DE HUANCA", tipo_vehiculo=TipoVehiculo.MOTOCICLETA),
        Association(nombre="ASOC. VIRGEN DE COPACABANA", tipo_vehiculo=TipoVehiculo.MOTOCICLETA),
        Association(nombre="ASOC. LOS ANDES", tipo_vehiculo=TipoVehiculo.MOTOCICLETA),
        Association(nombre="EMPRESA TAXI TOUR JULIACA", tipo_vehiculo=TipoVehiculo.LIVIANO),
    ]
    session.add_all(asociaciones)
    await session.flush()

    hoy = today()
    principal = fiscalizadores[0]

    vehiculos = [
        Vehicle(
            placa="A3H-451",
            propietario_nombre="JUAN CARLOS QUISPE MAMANI",
            propietario_dni="45781203",
            marca_modelo="BAJAJ RE 205 4T",
            nro_motor="AEMBTG12345",
            anio=2021,
            color="AZUL",
            asociacion_id=asociaciones[0].id,
            estado_permiso=EstadoPermiso.VIGENTE,
            fecha_emision=hoy - timedelta(days=200),
            fecha_vencimiento=hoy + timedelta(days=165),
            created_by_user_id=principal.id,
        ),
        Vehicle(
            placa="M2K-889",
            propietario_nombre="MARIA ELENA CONDORI APAZA",
            propietario_dni="42310998",
            marca_modelo="HONDA CG 125 CARGO",
            nro_motor="JC30E9012233",
            anio=2019,
            color="ROJO",
            asociacion_id=asociaciones[1].id,
            estado_permiso=EstadoPermiso.VENCIDO,
            fecha_emision=hoy - timedelta(days=400),
            fecha_vencimiento=hoy - timedelta(days=35),
            created_by_user_id=principal.id,
        ),
        Vehicle(
            placa="V7B-233",
            propietario_nombre="PEDRO ALBERTO HUAMAN ROJAS",
            propietario_dni="40889123",
            marca_modelo="TOYOTA YARIS 1.3",
            nro_motor="2NZ7745512",
            anio=2018,
            color="PLATA",
            asociacion_id=asociaciones[3].id,
            estado_permiso=EstadoPermiso.VIGENTE,
            fecha_emision=hoy - timedelta(days=90),
            fecha_vencimiento=hoy + timedelta(days=20),
            alerta_robo=True,
            created_by_user_id=fiscalizadores[1].id,
        ),
        Vehicle(
            placa="W5T-102",
            propietario_nombre="ROSA MERCEDES TICONA CHOQUE",
            propietario_dni="43920011",
            marca_modelo="TVS KING DELUXE",
            nro_motor="TVSK8891233",
            anio=2022,
            color="VERDE",
            asociacion_id=asociaciones[2].id,
            estado_permiso=EstadoPermiso.EN_TRAMITE,
            created_by_user_id=principal.id,
        ),
        Vehicle(
            placa="B8N-774",
            propietario_nombre="VICTOR MANUEL APAZA HUANCA",
            propietario_dni="44120876",
            marca_modelo="WANXIN WX 200 ZH",
            nro_motor="WX200ZH7741",
            anio=2020,
            color="NEGRO",
            asociacion_id=asociaciones[0].id,
            estado_permiso=EstadoPermiso.VIGENTE,
            fecha_emision=hoy - timedelta(days=150),
            fecha_vencimiento=hoy + timedelta(days=215),
            en_circulacion=False,
            created_by_user_id=fiscalizadores[1].id,
        ),
    ]
    for vehiculo in vehiculos:
        vehiculo.codigo_qr = uuid.uuid4().hex
    session.add_all(vehiculos)
    await session.flush()

    ahora = utcnow()
    session.add_all(
        [
            Inspection(
                vehicle_id=vehiculos[0].id,
                inspector_id=principal.id,
                tipo_inspeccion="RUTINARIA",
                estado_resultado=EstadoResultado.APROBADO,
                fecha=ahora - timedelta(hours=2),
                ubicacion="Jr. San Román con Av. Huancané",
                observaciones="Documentación en regla.",
            ),
            Inspection(
                vehicle_id=vehiculos[1].id,
                inspector_id=principal.id,
                tipo_inspeccion="OPERATIVO",
                estado_resultado=EstadoResultado.RECHAZADO,
                fecha=ahora - timedelta(hours=5),
                ubicacion="Plaza Bolognesi",
                observaciones="Permiso vencido hace más de 30 días.",
            ),
            Inspection(
                vehicle_id=vehiculos[2].id,
                inspector_id=fiscalizadores[1].id,
                tipo_inspeccion="DENUNCIA",
                estado_resultado=EstadoResultado.PENDIENTE,
                fecha=ahora - timedelta(days=1),
                ubicacion="Av. Circunvalación",
                observaciones="Vehículo con alerta de robo. Derivado a la PNP.",
            ),
            Inspection(
                vehicle_id=vehiculos[4].id,
                inspector_id=fiscalizadores[1].id,
                tipo_inspeccion="RUTINARIA",
                estado_resultado=EstadoResultado.APROBADO,
                fecha=ahora - timedelta(days=2),
                ubicacion="Terminal Terrestre",
            ),
        ]
    )

    await session.commit()
    logger.info(
        "Seed completado: %d fiscalizadores, %d vehículos. Contraseña demo: %s",
        len(fiscalizadores),
        len(vehiculos),
        DEMO_PASSWORD,
    )


async def seed_database() -> None:
    async with AsyncSessionLocal() as session:
        await _seed(session)


async def _main() -> None:
    await init_models()
    await seed_database()


if __name__ == "__main__":
    asyncio.run(_main())
