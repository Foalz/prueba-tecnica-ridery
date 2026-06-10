import { Router, Request, Response, NextFunction } from 'express';
import { syncTripsToOdoo } from '../services/odoo.service';
import { readTrips, writeTrips } from '../utils/fileManager';
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

/**
 * POST /api/v1/trips/reset-demo
 * Restaura la data de prueba a su estado original para permitir nuevas pruebas de sincronización.
 */
router.post('/reset-demo', async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const INITIAL_DATA = [
      {
        "trip_uuid": "a1b2c3d4-e001",
        "passenger_vat": "V-11111111",
        "driver_vat": "V-87654321",
        "distance_km": 8.4,
        "fare": 15.5,
        "status": "completed",
        "requested_at": "2026-06-10T07:00:00.000Z",
        "stops": [
          { "name": "Plaza Altamira", "type": "start", "lat": 10.4965, "lng": -66.8488 },
          { "name": "C.C. San Ignacio", "type": "intermediate", "lat": 10.492, "lng": -66.852 },
          { "name": "Centro Lido", "type": "intermediate", "lat": 10.488, "lng": -66.855 },
          { "name": "C.C. Sambil", "type": "end", "lat": 10.4855, "lng": -66.857 }
        ],
        "odoo_id": null,
        "odoo_reference": null,
        "synced_at": null,
        "sync_error": null
      },
      {
        "trip_uuid": "a1b2c3d4-e002",
        "passenger_vat": "V-22222222",
        "driver_vat": "V-98765432",
        "distance_km": 12.1,
        "fare": 22,
        "status": "in_progress",
        "requested_at": "2026-06-10T07:30:00.000Z",
        "stops": [
          { "name": "Las Mercedes", "type": "start", "lat": 10.48, "lng": -66.865 },
          { "name": "El Hatillo", "type": "end", "lat": 10.428, "lng": -66.822 }
        ],
        "odoo_id": null,
        "odoo_reference": null,
        "synced_at": null,
        "sync_error": null
      }
    ];

    // Escribimos la data inicial usando writeTrips pero con un cast ya que writeTrips espera RawTrip[]
    await writeTrips(INITIAL_DATA as any);

    logger.info('Data de prueba restaurada exitosamente.', { event: 'reset_demo_trigger' });

    res.status(200).json({
      ok: true,
      message: 'Data de prueba restaurada a su estado original.'
    });
  } catch (err) {
    next(err);
  }
});

export default router;
