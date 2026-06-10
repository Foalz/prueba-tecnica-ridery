import winston from 'winston';
import DailyRotateFile from 'winston-daily-rotate-file';
import path from 'path';

const LOG_DIR = path.resolve(process.cwd(), 'logs');

const fileFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.errors({ stack: true }),
  winston.format.json(),
);

const consoleFormat = winston.format.combine(
  winston.format.colorize({ all: true }),
  winston.format.timestamp({ format: 'HH:mm:ss' }),
  winston.format.printf(({ timestamp, level, message, ...meta }) => {
    const extra = Object.keys(meta).length ? `\n${JSON.stringify(meta, null, 2)}` : '';
    return `[${timestamp}] ${level}: ${message}${extra}`;
  }),
);

const logger = winston.createLogger({
  level: 'info',
  transports: [
    new winston.transports.Console({ format: consoleFormat }),

    // Todos los logs — rotación diaria, 14 días de retención
    new DailyRotateFile({
      dirname: LOG_DIR,
      filename: 'ridery-%DATE%.log',
      datePattern: 'YYYY-MM-DD',
      maxFiles: '14d',
      zippedArchive: true,
      format: fileFormat,
    }),

    // Solo errores — 30 días de retención
    new DailyRotateFile({
      dirname: LOG_DIR,
      filename: 'ridery-error-%DATE%.log',
      datePattern: 'YYYY-MM-DD',
      level: 'error',
      maxFiles: '30d',
      zippedArchive: true,
      format: fileFormat,
    }),
  ],
});

// Stream para redirigir Morgan → Winston
export const morganStream = {
  write: (message: string) => logger.info(message.trimEnd(), { event: 'http_request' }),
};

// Helper tipado para registrar llamadas al endpoint de Odoo
export interface OdooCallLog {
  status: 'success' | 'partial' | 'error';
  endpoint: string;
  message: string;
  httpStatus?: number;
  received?: number;
  created?: number;
  failed?: number;
  errors?: Array<{ trip_uuid: string; message: string }>;
}

export function logOdooCall(params: OdooCallLog): void {
  const level = params.status === 'success' ? 'info'
    : params.status === 'partial' ? 'warn'
    : 'error';

  logger[level](`[Odoo] ${params.message}`, {
    event: 'odoo_api_call',
    date: new Date().toISOString(),
    ...params,
  });
}

export default logger;
