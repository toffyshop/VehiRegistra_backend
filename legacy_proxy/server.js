require('dotenv').config();
const express = require('express');
const cors = require('cors');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 3000;

// Enable CORS so the Android emulator/device can connect
app.use(cors());
app.use(express.json());

// Log requests
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  next();
});

// Endpoint to query plates
app.get('/api/placa/:placa', async (req, res) => {
  const { placa } = req.params;
  const cleanPlaca = placa.trim().toUpperCase().replace(/[^A-Z0-9-]/g, '');

  if (!cleanPlaca) {
    return res.status(400).json({
      success: false,
      message: 'Placa no válida'
    });
  }

  const token = process.env.API_TOKEN;
  if (!token) {
    console.error('Error: API_TOKEN no configurado en el archivo .env');
    return res.status(500).json({
      success: false,
      message: 'Error de configuración en el servidor'
    });
  }

  try {
    const url = `https://api2.consultadatos.com/api/placa/leyenda/${cleanPlaca}`;
    console.log(`Consultando API externa para placa: ${cleanPlaca}`);

    const response = await axios.get(url, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/json'
      },
      timeout: 10000 // 10 seconds timeout
    });

    console.log(`API externa respondió con éxito para placa: ${cleanPlaca}`);
    return res.json(response.data);

  } catch (error) {
    console.error(`Error consultando placa ${cleanPlaca}:`, error.message);
    
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('Detalle error externo:', error.response.status, error.response.data);
      return res.status(error.response.status).json(error.response.data);
    } else if (error.request) {
      // The request was made but no response was received
      return res.status(503).json({
        success: false,
        message: 'No se recibió respuesta del servicio externo de SUNARP'
      });
    } else {
      // Something happened in setting up the request that triggered an Error
      return res.status(500).json({
        success: false,
        message: 'Error interno al procesar la solicitud'
      });
    }
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', time: new Date() });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`==================================================`);
  console.log(` Servidor Proxy VehiRegistro corriendo exitosamente`);
  console.log(` Puerto local: http://localhost:${PORT}`);
  console.log(` Dirección LAN: http://<tu-ip-local>:${PORT}`);
  console.log(`==================================================`);
});
