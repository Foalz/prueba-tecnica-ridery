import { Router, Request, Response, NextFunction } from 'express';
import { syncTripsToOdoo } from '../services/odoo.service';
import { readTrips } from '../utils/fileManager';
import logger from '../utils/logger';

const router = Router();

/**
 * POST /api/v1/trips
 * Sincroniza todos los viajes pendientes desde trips.json hacia Odoo.
 */
router.post('/', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    logger.info('Iniciando petición de sincronización manual...', { event: 'manual_sync_trigger' });
    const result = await syncTripsToOdoo();

    res.status(200).json({
      ok: result.failed === 0,
      message:
        result.pending === 0
          ? 'No hay viajes pendientes para sincronizar.'
          : `Sincronización finalizada: ${result.created} exitosos, ${result.failed} fallidos.`,
      data: result,
    });
  } catch (err) {
    // Si algo falla estrepitosamente, lo pasamos al errorHandler
    next(err);
  }
});

/**
 * GET /api/v1/trips
 * Retorna la lista completa de viajes directamente desde el archivo trips.json.
 */
router.get('/', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const trips = await readTrips();

    res.status(200).json({
      ok: true,
      data: trips,
    });
  } catch (err) {
    next(err);
  }
});

export default router;
