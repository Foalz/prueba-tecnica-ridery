import axios, { isAxiosError } from 'axios';
import { env, ODOO_ENDPOINT } from '../config/env';
import { RawTrip, OdooTrip, OdooTripState, OdooApiResponse, SyncResult } from '../types/trip.types';
import { readTrips, writeTrips } from '../utils/fileManager';
import { logOdooCall } from '../utils/logger';

// ── Mapeo de estados ──────────────────────────────────────────────────────────

const STATUS_MAP: Record<string, OdooTripState> = {
  pending:     'draft',
  confirmed:   'confirmed',
  in_route:    'in_progress',
  in_progress: 'in_progress',
  cancelled:   'cancelled',
};

// ── Transformación ────────────────────────────────────────────────────────────

function toOdooPayload(trip: RawTrip): OdooTrip {
  return {
    passenger_vat: trip.passenger_vat,
    driver_vat:    trip.driver_vat,
    distance:      trip.distance_km,
    price:         trip.fare,
    state:         STATUS_MAP[trip.status] ?? 'draft',
    city:          trip.city,
    start_address: trip.start_address,
    end_address:   trip.end_address,
  };
}

// ── Servicio principal ────────────────────────────────────────────────────────

export async function syncTripsToOdoo(): Promise<SyncResult> {
  const allTrips = await readTrips();

  // Solo viajes sin sincronizar y sin error previo
  const pending = allTrips.filter(
    (t) => t.synced_at === null && t.sync_error === null,
  );

  if (pending.length === 0) {
    logOdooCall({
      status: 'success',
      endpoint: ODOO_ENDPOINT,
      message: 'No hay viajes pendientes de sincronización',
      received: 0, created: 0, failed: 0,
    });
    return { total: allTrips.length, pending: 0, created: 0, failed: 0, errors: [] };
  }

  // ── Llamada a Odoo ────────────────────────────────────────────────────────
  let odooResponse: OdooApiResponse;
  let httpStatus: number;

  try {
    const res = await axios.post<OdooApiResponse>(
      ODOO_ENDPOINT,
      pending.map(toOdooPayload),
      {
        headers: {
          'Content-Type': 'application/json',
          'Origin':        env.ODOO_ORIGIN,
          'X-API-Key':     env.ODOO_API_KEY,
        },
        validateStatus: (s) => s < 500,
        timeout: 30_000,
      },
    );
    odooResponse = res.data;
    httpStatus   = res.status;
  } catch (err) {
    const message = isAxiosError(err)
      ? `Error de red: ${err.message}`
      : `Error inesperado: ${String(err)}`;
    logOdooCall({ status: 'error', endpoint: ODOO_ENDPOINT, message });
    throw new Error(message);
  }

  // ── Errores de autenticación / CORS ───────────────────────────────────────
  if (httpStatus === 401 || httpStatus === 403) {
    const message = odooResponse.message ?? `HTTP ${httpStatus}`;
    logOdooCall({ status: 'error', endpoint: ODOO_ENDPOINT, message, httpStatus });
    throw new Error(message);
  }

  // ── Mapear resultados al array original ───────────────────────────────────
  //
  // Odoo devuelve:
  //   trips[]  → viajes creados, en orden de los NO-errores del input
  //   errors[] → { index, message } donde index = posición en el array enviado
  //
  const errorIndexSet = new Set(odooResponse.errors.map((e) => e.index));
  const syncErrors: SyncResult['errors'] = [];
  const now = new Date().toISOString();
  let createdCursor = 0;

  for (let i = 0; i < pending.length; i++) {
    const idx = allTrips.findIndex((t) => t.trip_uuid === pending[i].trip_uuid);

    if (errorIndexSet.has(i)) {
      const detail = odooResponse.errors.find((e) => e.index === i);
      allTrips[idx].sync_error = detail?.message ?? 'Error desconocido';
      syncErrors.push({ trip_uuid: pending[i].trip_uuid, message: allTrips[idx].sync_error! });
    } else {
      const created = odooResponse.trips[createdCursor++];
      allTrips[idx].odoo_id        = created.id;
      allTrips[idx].odoo_reference = created.name;
      allTrips[idx].synced_at      = now;
      allTrips[idx].sync_error     = null;
    }
  }

  await writeTrips(allTrips);

  // ── Log de evidencia ──────────────────────────────────────────────────────
  const statusLabel =
    odooResponse.status === 'ok' ? 'success' :
    odooResponse.status === 'partial' ? 'partial' : 'error';

  logOdooCall({
    status:     statusLabel,
    endpoint:   ODOO_ENDPOINT,
    message:    `${odooResponse.created} creados, ${odooResponse.errors.length} con error de ${pending.length} enviados`,
    httpStatus,
    received:   odooResponse.received,
    created:    odooResponse.created,
    failed:     odooResponse.errors.length,
    errors:     syncErrors,
  });

  return {
    total:   allTrips.length,
    pending: pending.length,
    created: odooResponse.created,
    failed:  odooResponse.errors.length,
    errors:  syncErrors,
  };
}
