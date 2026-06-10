import express from 'express';
import morgan from 'morgan';
import { morganStream } from './utils/logger';
import tripsRouter from './routes/trips.routes';
import { errorHandler } from './middleware/errorHandler';

const app = express();
app.use(express.json());

app.use(morgan('combined', { stream: morganStream }));

app.get('/health', (_req, res) => {
  res.json({
    ok: true,
    service: 'ridery-node-api',
    timestamp: new Date().toISOString(),
  });
});

app.use('/api/v1/trips', tripsRouter);

app.use(errorHandler);

export default app;
