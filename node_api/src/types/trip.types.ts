export interface RawTrip {
  trip_uuid: string;
  /** RIF/Cédula del pasajero — formato venezolano: V-12345678 */
  passenger_vat: string;
  /** RIF/Cédula del conductor — formato venezolano: V-87654321 */
  driver_vat: string;
  distance_km: number;
  fare: number;
  status: AppTripStatus;
  requested_at: string;
  city: string;
  start_address: string;
  end_address: string;

  odoo_id: number | null;
  odoo_reference: string | null;
  synced_at: string | null;
  sync_error: string | null;
}

export type AppTripStatus =
  | 'pending'
  | 'confirmed'
  | 'in_route'
  | 'in_progress'
  | 'completed'
  | 'cancelled';

export interface OdooTrip {
  passenger_vat: string;
  driver_vat: string;
  distance: number;
  price: number;
  state?: OdooTripState;
  city: string;
  start_address: string;
  end_address: string;
}

export type OdooTripState = 'draft' | 'confirmed' | 'in_progress' | 'cancelled';

export interface OdooCreatedTrip {
  id: number;
  name: string;
}

export interface OdooApiResponse {
  status: 'ok' | 'partial' | 'error';
  received: number;
  created: number;
  trips: OdooCreatedTrip[];
  errors: Array<{ index: number; message: string }>;
  message?: string;
}

export interface SyncResult {
  total: number;
  pending: number;
  created: number;
  failed: number;
  errors: Array<{ trip_uuid: string; message: string }>;
}
