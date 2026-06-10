import app from './app';
import { env, ODOO_ENDPOINT } from './config/env';
import logger from './utils/logger';

const server = app.listen(env.PORT, () => {
  logger.info(`🚀 Ridery Node API corriendo en http://localhost:${env.PORT}`, {
    event: 'server_start',
    port: env.PORT,
    env: env.NODE_ENV,
    odoo_endpoint: ODOO_ENDPOINT,
  });
});

function gracefulShutdown(signal: string) {
  logger.info(`${signal} recibido — cerrando servidor ordenadamente...`);
  server.close(() => {
    logger.info('Servidor HTTP cerrado exitosamente.');
    process.exit(0);
  });
}

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));
