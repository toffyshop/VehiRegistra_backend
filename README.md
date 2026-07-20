# VehiRegistro API 🚦

API RESTful del **Sistema de Fiscalización Municipal de Vehículos y Mototaxis**, construida con
FastAPI, SQLAlchemy 2.0 (async) y Pydantic v2.

> Reemplaza al proxy Node que ocupaba antes este repositorio, conservado en `legacy_proxy/`
> como referencia de la integración con la API real de placas. Aquí la consulta de placas
> está implementada como **mock**; más abajo se documenta cómo conectar el proveedor real.

## 🏗️ Arquitectura

```
app/
├── main.py                  # Creación de la app, CORS, static, lifespan
├── core/                    # Configuración transversal
│   ├── config.py            # Settings desde .env (pydantic-settings)
│   ├── database.py          # Engine async + sesión por request
│   ├── security.py          # bcrypt (passlib) + JWT (PyJWT)
│   ├── exceptions.py        # Excepciones de dominio + handlers globales
│   └── logging.py
├── models/                  # Capa ORM (SQLAlchemy 2.0, Mapped[])
│   ├── base.py  enums.py  user.py  association.py  vehicle.py  inspection.py
├── schemas/                 # Capa Pydantic v2 (contratos de la API)
│   ├── common.py  auth.py  user.py  vehicle.py  inspection.py
│   ├── association.py  sunarp.py  dashboard.py
├── services/                # Lógica de negocio (sin dependencias de HTTP)
│   ├── auth_service.py  user_service.py  vehicle_service.py
│   ├── inspection_service.py  dashboard_service.py
│   ├── sunarp_service.py  storage_service.py  association_service.py
├── api/
│   ├── deps.py              # Sesión, usuario autenticado, paginación
│   └── v1/
│       ├── router.py
│       └── endpoints/       # auth, users, dashboard, reports, external,
│                            # vehicles, inspections, associations
└── db/seed.py               # Datos de demostración (idempotente)

legacy_proxy/                # Proxy Node anterior. Referencia, no se despliega.
```

**Regla de dependencias:** `endpoints → services → models`. Los servicios no conocen FastAPI,
así que la lógica de negocio es testeable sin levantar el servidor.

## 🚀 Puesta en marcha

```powershell
cd VehiRegistra_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Copy-Item .env.example .env      # ajustar SECRET_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Al arrancar en modo `dev` se crean las tablas y se cargan datos de demostración.

* Swagger UI → <http://localhost:8000/docs>
* ReDoc → <http://localhost:8000/redoc>
* Health check → <http://localhost:8000/health>

### Usuarios de demostración

| Código  | DNI      | Email                   | Contraseña    |
|---------|----------|-------------------------|---------------|
| FIS-001 | 70112233 | j.ramirez@muni.gob.pe   | `Fiscal2026!` |
| FIS-002 | 70445566 | l.torres@muni.gob.pe    | `Fiscal2026!` |
| FIS-100 | 88776655 | prueba@muni.gob.pe      | `Prueba2026!` |

* `POST /auth/login/json` → se inicia sesión con **email**.
* `POST /auth/login` (OAuth2) → el campo `username` acepta **DNI, código o email**.

### Crear más usuarios

`seed.py` sólo actúa sobre una base vacía. Para dar de alta un fiscalizador en cualquier
momento:

```powershell
python -m app.db.create_user --email fiscal@muni.gob.pe --password "Clave123!" `
    --dni 12345678 --code FIS-010 --nombre "NOMBRE APELLIDO"
```

### Conexión desde el emulador Android

`10.0.2.2` es el host desde el emulador. En `.env`:

```
PUBLIC_BASE_URL=http://10.0.2.2:8000
BACKEND_CORS_ORIGINS=*
```

Para un dispositivo físico use la IP LAN de la PC y arranque uvicorn con `--host 0.0.0.0`.

## 📍 Endpoints

Todos requieren `Authorization: Bearer <token>` salvo `/auth/login`, `/health` y `/`.

### Auth
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/auth/login` | OAuth2 Password Flow (form-urlencoded) |
| POST | `/api/v1/auth/login/json` | Misma operación con cuerpo JSON |
| GET  | `/api/v1/auth/verify` | Comprueba si el token sigue vigente |

### Usuarios
| Método | Ruta | Descripción |
|---|---|---|
| GET  | `/api/v1/users/me` | Perfil + `total_registros`, `total_fiscalizaciones`, `registros_mes_actual` |
| PUT  | `/api/v1/users/me` | Editar perfil (parcial; `dni` y `code` son inmutables) |
| POST | `/api/v1/users/me/change-password` | Cambio de contraseña |

### Dashboard y reportes
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/dashboard/summary` | Inspecciones/registros de hoy, alertas, permisos por vencer, estado del sistema |
| GET | `/api/v1/reports/stats` | Totales por estado, desglose por asociación y tipo de vehículo, inspecciones recientes |

### Integración SUNARP
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/external/sunarp/{placa}` | Datos del vehículo y propietario para autocompletar el formulario |

### Vehículos
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/vehicles` | Registro (`multipart/form-data`, campo `photo` opcional) |
| GET  | `/api/v1/vehicles` | Listado paginado: `page`, `size`, `estado`, `search`, `asociacion_id`, `solo_alertas` |
| GET  | `/api/v1/vehicles/{placa}` | Detalle por placa **o** código QR |
| PUT  | `/api/v1/vehicles/{id}` | Actualización parcial |
| PUT  | `/api/v1/vehicles/{id}/renew` | Renovación del permiso |
| PUT  | `/api/v1/vehicles/{id}/photo` | Reemplazo de la fotografía |

`search` busca simultáneamente en placa, DNI del propietario, nombre y marca/modelo.

### Fiscalizaciones
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/inspections` | Inspección rápida (identifica por `vehicle_id` o `placa`) |
| GET  | `/api/v1/inspections/recent` | Últimas inspecciones (`limit`, `only_mine`, `vehicle_id`, `estado`) |

### Asociaciones
| Método | Ruta | Descripción |
|---|---|---|
| GET  | `/api/v1/associations` | Catálogo para el selector del formulario |
| POST | `/api/v1/associations` | Alta de asociación |

## 📦 Formato de respuestas

Los recursos se devuelven directamente. Los **listados paginados** usan:

```json
{ "items": [ ... ], "meta": { "total": 42, "page": 1, "size": 20, "pages": 3,
                              "has_next": true, "has_prev": false } }
```

Los **errores** siempre tienen la misma forma, generada por los handlers globales:

```json
{
  "success": false,
  "error": {
    "code": "validation_error",
    "message": "Uno o más campos no superaron la validación.",
    "details": [{ "field": "propietario_dni", "message": "String should match pattern '^\\d{8}$'",
                  "type": "string_pattern_mismatch" }]
  },
  "path": "/api/v1/vehicles",
  "timestamp": "2026-07-20T16:30:03.601277+00:00"
}
```

| Código | Cuándo |
|---|---|
| 200 / 201 | Operación exitosa / recurso creado |
| 400 | Fotografía inválida, vacía o superior a `MAX_UPLOAD_SIZE_MB` |
| 401 | Credenciales incorrectas, token inválido/expirado, contraseña actual errónea |
| 403 | Cuenta desactivada |
| 404 | Vehículo, asociación o placa inexistente |
| 409 | Placa duplicada, email en uso, renovación con fecha no futura |
| 422 | Validación de esquema (placa/DNI mal formados, enum inválido, faltan campos) |
| 500 / 502 | Error interno / servicio externo caído |

## 🔌 Conectar el servicio SUNARP real

`app/services/sunarp_service.py` aísla la integración en `_fetch_external()`. Para usar el
proveedor real (el mismo que consume `legacy_proxy/server.js`):

1. Añadir `httpx` a `requirements.txt` y `SUNARP_API_URL` / `SUNARP_API_TOKEN` a `config.py`.
2. Reemplazar el cuerpo de `_fetch_external` por la llamada HTTP y mapear la respuesta al
   diccionario que ya consume `consultar_placa`.
3. Envolver los fallos de red en `ExternalServiceError` para que respondan 502 con el envelope
   estándar.

Ningún otro archivo necesita cambios.

## 🧪 Decisiones de diseño

* **Fechas de permiso.** El enunciado no las incluye, pero sin `fecha_vencimiento` no es
  posible calcular "permisos vencidos" ni implementar la renovación. Se añadieron
  `fecha_emision` y `fecha_vencimiento` a `Vehicle`.
* **Estado calculado en lectura.** Un permiso `VIGENTE` cuya fecha ya pasó se muestra como
  `VENCIDO` sin depender de un job nocturno (`_apply_expiry_state`).
* **Código QR.** `Vehicle.codigo_qr` (UUID) permite que `GET /vehicles/{placa}` resuelva tanto
  por placa como por el código escaneado de la calcomanía.
* **Placas normalizadas.** `a3h451`, `A3H 451` y `A3H-451` se guardan y consultan como
  `A3H-451`, evitando duplicados en el padrón.
* **Fotografía antes del insert.** La imagen se valida y guarda antes de crear el registro, y
  se borra si el insert falla: no quedan archivos huérfanos ni vehículos sin foto.
* **UTC naive.** SQLite no conserva `tzinfo`; se almacena UTC sin zona (`models/base.utcnow`)
  para que las comparaciones en las queries sean consistentes entre SQLite y PostgreSQL.
* **Login resistente a enumeración.** Si el usuario no existe se ejecuta un hash descartable,
  para que el tiempo de respuesta no revele qué identificadores están registrados.

## 🐘 Producción

1. `DATABASE_URL=postgresql+asyncpg://…` (el código es agnóstico del motor).
2. `ENVIRONMENT=prod` y `SEED_ON_STARTUP=false`.
3. `SECRET_KEY` fuerte y `BACKEND_CORS_ORIGINS` restringido a los orígenes reales.
4. Sustituir `init_models()` por migraciones Alembic (los nombres de constraints ya siguen una
   convención explícita en `models/base.py`).
5. Servir las fotografías desde S3/Azure Blob reimplementando `storage_service`.
