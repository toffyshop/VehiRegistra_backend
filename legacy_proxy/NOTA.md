# Proxy Node (referencia histórica)

Servidor Express que consultaba **la API real de placas** (`api2.consultadatos.com`).
Fue el primer backend del proyecto; hoy su función la cumple la API FastAPI de la carpeta
raíz, donde la consulta está implementada como **mock** en
`app/services/sunarp_service.py`.

Se conserva aquí como referencia del formato de la integración real: si se decide conectar
el proveedor de verdad, `server.js` muestra la URL, la cabecera `Authorization: Bearer` y el
manejo de errores que esperaba el proveedor.

**No se ejecuta ni se despliega.** El README de la raíz explica, en la sección
"Conectar el servicio SUNARP real", los pasos para llevar esta lógica a `sunarp_service.py`.

Requiere `API_TOKEN` en un `.env` propio si alguna vez se levanta con `node server.js`.
