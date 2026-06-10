import { Request, Response, NextFunction } from 'express';
import logger from '../utils/logger';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function errorHandler(err: Error, req: Request, res: Response, _next: NextFunction): void {
  // Logueamos el error usando nuestro logger de Winston
  logger.error(`Unhandled Error: ${err.message}`, {
    event: 'unhandled_error',
    stack: err.stack,
    method: req.method,
    path: req.path,
  });

  // Devolvemos una respuesta JSON limpia al cliente
  res.status(500).json({
    ok: false,
    message: err.message || 'Internal Server Error',
  });
}
