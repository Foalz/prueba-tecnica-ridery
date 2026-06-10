import express from 'express';
import morgan from 'morgan';
import { morganStream } from './utils/logger';
import tripsRouter from './routes/trips.routes';
import { errorHandler } from './middleware/errorHandler';

const app = express();

// ── Middlewares globales ───────────────────────────────────────────────────────
app.use(express.json());

// Morgan registrará todas las peticiones HTTP y las enviará a Winston
app.use(morgan('combined', { stream: morganStream }));

// ── Rutas ─────────────────────────────────────────────────────────────────────

// Health check para balanceadores de carga / Docker
app.get('/health', (_req, res) => {
  res.json({
    ok: true,
    service: 'ridery-node-api',
    timestamp: new Date().toISOString(),
  });
});

// Rutas de la API de viajes
app.use('/api/v1/trips', tripsRouter);

// ── Manejo de Errores ─────────────────────────────────────────────────────────
// ¡Importante! El errorHandler debe ser el último middleware inyectado
app.use(errorHandler);

export default app;
