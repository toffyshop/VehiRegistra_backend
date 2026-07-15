# VehiRegistra Backend Proxy 🚀

Servidor proxy intermedio para enrutar consultas de placas de la aplicación móvil **VehiRegistro** hacia la API de Consultas Datos, protegiendo las credenciales en producción.

## 🛠️ Requisitos
*   [Node.js](https://nodejs.org/) v18 o superior.

## 💻 Instalación y Ejecución

1.  Navega al directorio del backend:
    ```bash
    cd VehiRegistra_backend
    ```
2.  Instala las dependencias:
    ```bash
    npm install
    ```
3.  Inicia el servidor en modo desarrollo (se reinicia automáticamente con los cambios):
    ```bash
    npm run dev
    ```
    O en modo de producción:
    ```bash
    npm start
    ```

## 📍 Endpoints Disponibles

### 🚗 Buscar Placa Vehicular
*   **Método**: `GET`
*   **Ruta**: `/api/placa/:placa`
*   **Respuesta**: Devuelve el JSON con la información de SUNARP (propietario, marca, modelo, etc.).
*   **Ejemplo**: `http://localhost:3000/api/placa/A3H451`
