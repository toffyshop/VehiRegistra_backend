"""Alta de fiscalizadores desde la línea de comandos.

A diferencia de `seed.py`, que sólo actúa sobre una base vacía, este script
funciona en cualquier momento. Útil para crear cuentas de prueba o el primer
usuario en un despliegue nuevo.

    python -m app.db.create_user --email fiscal@muni.gob.pe --password "Clave123!" \
        --dni 12345678 --code FIS-010 --nombre "NOMBRE APELLIDO"

Si se omite un dato opcional se usa un valor por defecto razonable.
"""

import argparse
import asyncio
import sys

from pydantic import ValidationError

from app.core.database import AsyncSessionLocal, init_models
from app.core.exceptions import ConflictError
from app.schemas.user import UserCreate
from app.services import user_service


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crea un fiscalizador.")
    parser.add_argument("--email", required=True, help="Correo institucional")
    parser.add_argument("--password", required=True, help="Mínimo 8 caracteres")
    parser.add_argument("--dni", required=True, help="8 dígitos")
    parser.add_argument("--code", required=True, help="Código, ej. FIS-010")
    parser.add_argument("--nombre", required=True, help="Nombre completo")
    parser.add_argument("--area", default="Fiscalización de Tránsito")
    parser.add_argument("--phone", default=None)
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    try:
        payload = UserCreate(
            email=args.email,
            password=args.password,
            dni=args.dni,
            code=args.code,
            full_name=args.nombre,
            area=args.area,
            phone=args.phone,
        )
    except ValidationError as exc:
        print("Datos inválidos:", file=sys.stderr)
        for error in exc.errors():
            campo = ".".join(str(p) for p in error["loc"])
            print(f"  - {campo}: {error['msg']}", file=sys.stderr)
        return 2

    await init_models()
    async with AsyncSessionLocal() as session:
        try:
            user = await user_service.create_user(session, payload)
        except ConflictError as exc:
            print(f"No se pudo crear: {exc.message}", file=sys.stderr)
            return 1

    print("Fiscalizador creado correctamente:")
    print(f"  id     : {user.id}")
    print(f"  email  : {user.email}")
    print(f"  dni    : {user.dni}")
    print(f"  código : {user.code}")
    print(f"  nombre : {user.full_name}")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_run(_parse_args())))


if __name__ == "__main__":
    main()
