# -*- coding: utf-8 -*-
import json
import logging
import re

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

VALID_STATES = {'draft', 'confirmed', 'in_progress', 'cancelled'}

# Mismo regex que l10n_ve_custom — V-12345678 / E-12345678 / J-123456789
VE_VAT_REGEX = re.compile(r'^[VvEeJjGgPp]-?\d{7,9}$')

_CORS_HEADERS_BASE = {
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
    'Access-Control-Max-Age': '86400',
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_param(env, key, default=''):
    return env['ir.config_parameter'].sudo().get_param(key, default)


def _json_response(data, status=200, origin=None):
    headers = {'Content-Type': 'application/json'}
    if origin:
        headers['Access-Control-Allow-Origin'] = origin
    headers.update(_CORS_HEADERS_BASE)
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status,
        headers=list(headers.items()),
    )


def _normalize_vat(vat):
    """Normaliza la cédula a mayúsculas y sin espacios."""
    return vat.strip().upper().replace(' ', '') if vat else ''


def _resolve_partner(env, vat_raw, expected_role, field_label):
    """
    Busca un res.partner por su RIF/Cédula venezolano y verifica su rol Ridery.

    Retorna (partner_id: int, None) si es válido,
    o (None, error_message: str) si hay algún problema.
    """
    vat = _normalize_vat(vat_raw)

    # 1. Formato válido
    if not VE_VAT_REGEX.match(vat):
        return None, (
            f"El campo '{field_label}' contiene un RIF/Cédula con formato inválido: "
            f"'{vat}'. Formatos aceptados: V-12345678, E-12345678, J-123456789, G-12345678."
        )

    # 2. Existe en el sistema
    partner = env['res.partner'].sudo().search(
        [('vat', '=ilike', vat)], limit=1
    )
    if not partner:
        return None, (
            f"No se encontró ningún contacto con el RIF/Cédula '{vat}' "
            f"para el campo '{field_label}'."
        )

    # 3. Tiene el rol correcto (Solo validamos al conductor)
    if expected_role == 'driver':
        if not partner.is_ridery_driver:
            return None, (
                f"El contacto '{partner.name}' (RIF/Cédula: {vat}) "
                f"no tiene ningún vehículo asignado en la Flota de Odoo, "
                f"por lo que no puede ser Conductor."
            )

    return partner.id, None


def _validate_trip(env, trip_data):
    """
    Valida los datos de un único viaje.

    Entrada esperada:
      {
        "passenger_vat": "V-12345678",
        "driver_vat":    "V-87654321",
        "distance":      8.4,
        "price":         15.50,
        "state":         "confirmed"   (opcional)
      }

    Retorna (vals_dict, None) si es válido,
    o (None, error_message) si hay errores.
    """
    errors = []

    # ── Campos requeridos ─────────────────────────────────────────────────────
    for field in ('passenger_vat', 'driver_vat', 'distance', 'price'):
        if field not in trip_data or trip_data[field] is None:
            errors.append(f"Campo requerido ausente: '{field}'")

    if errors:
        return None, '; '.join(errors)

    # ── Tipos numéricos ───────────────────────────────────────────────────────
    try:
        distance = float(trip_data['distance'])
        price    = float(trip_data['price'])
    except (TypeError, ValueError):
        return None, "'distance' y 'price' deben ser numéricos"

    if distance <= 0:
        errors.append("'distance' debe ser mayor que 0")
    if price < 0:
        errors.append("'price' no puede ser negativo")

    if errors:
        return None, '; '.join(errors)

    # ── Resolver pasajero por cédula ──────────────────────────────────────────
    passenger_id, err = _resolve_partner(
        env, trip_data['passenger_vat'], 'passenger', 'passenger_vat'
    )
    if err:
        return None, err

    # ── Resolver conductor por cédula ─────────────────────────────────────────
    driver_id, err = _resolve_partner(
        env, trip_data['driver_vat'], 'driver', 'driver_vat'
    )
    if err:
        return None, err

    # ── Pasajero ≠ Conductor ──────────────────────────────────────────────────
    if passenger_id == driver_id:
        return None, (
            "El pasajero y el conductor no pueden tener el mismo "
            f"RIF/Cédula ({_normalize_vat(trip_data['passenger_vat'])})."
        )

    # ── state (opcional) ──────────────────────────────────────────────────────
    state = trip_data.get('state', 'draft')
    if state not in VALID_STATES:
        return None, (
            f"'state' inválido: '{state}'. "
            f"Valores permitidos: {sorted(VALID_STATES)}"
        )

    # ── company_id (opcional) ─────────────────────────────────────────────────
    vals = {
        'partner_id':        passenger_id,
        'driver_partner_id': driver_id,
        'distance':          distance,
        'price':             price,
        'state':             state,

        'start_address':     trip_data.get('start_address'),
        'end_address':       trip_data.get('end_address'),
    }

    company_id = trip_data.get('company_id')
    if company_id is not None:
        if not isinstance(company_id, int):
            return None, "'company_id' debe ser un entero"
        company = env['res.company'].sudo().browse(company_id)
        if not company.exists():
            return None, f"La compañía con id={company_id} no existe"
        vals['company_id'] = company_id

    return vals, None


# ── Controlador ───────────────────────────────────────────────────────────────

class RideryTripsApiController(http.Controller):

    @http.route(
        '/ridery/api/v1/trips',
        type='http',
        auth='none',
        methods=['POST', 'OPTIONS'],
        csrf=False,
        cors=None,
        save_session=False,
    )
    def receive_trips(self, **kwargs):
        """
        Recibe un JSON de viajes y los registra en ridery.trips.

        Los contactos se identifican por RIF/Cédula venezolano,
        no por ID de base de datos.

        Headers requeridos:
            Origin:    debe coincidir con ridery.allowed_origin
            X-API-Key: debe coincidir con ridery.api_key

        Ejemplo de body:
        """
        env = request.env

        allowed_origin  = _get_param(env, 'ridery.allowed_origin', '').strip()
        api_key_stored  = _get_param(env, 'ridery.api_key', '').strip()
        origin          = request.httprequest.headers.get('Origin', '').strip()

        # ── Preflight OPTIONS ─────────────────────────────────────────────────
        if request.httprequest.method == 'OPTIONS':
            if allowed_origin and origin != allowed_origin:
                return Response('Forbidden', status=403)
            return _json_response({}, status=204, origin=origin or allowed_origin)

        # ── 1. Validar CORS ───────────────────────────────────────────────────
        if allowed_origin and origin != allowed_origin:
            _logger.warning(
                "Ridery API: Origin rechazado '%s' (permitido: '%s')",
                origin, allowed_origin,
            )
            return _json_response(
                {'status': 'error', 'message': 'Origin no permitido'},
                status=403,
            )

        # ── 2. Validar API Key ────────────────────────────────────────────────
        api_key_received = request.httprequest.headers.get('X-API-Key', '').strip()
        if not api_key_stored or api_key_received != api_key_stored:
            _logger.warning("Ridery API: API Key inválida o ausente")
            return _json_response(
                {'status': 'error', 'message': 'API Key inválida o ausente'},
                status=401,
                origin=origin,
            )

        # ── 3. Parsear body JSON ──────────────────────────────────────────────
        try:
            raw_body = request.httprequest.get_data(as_text=True)
            payload  = json.loads(raw_body)
        except (json.JSONDecodeError, Exception) as exc:
            return _json_response(
                {'status': 'error', 'message': f'JSON inválido: {exc}'},
                status=400,
                origin=origin,
            )

        if isinstance(payload, dict):
            trips_input = [payload]
        elif isinstance(payload, list):
            trips_input = payload
        else:
            return _json_response(
                {'status': 'error', 'message': 'El cuerpo debe ser un objeto o un array JSON'},
                status=400,
                origin=origin,
            )

        if not trips_input:
            return _json_response(
                {'status': 'error', 'message': 'El array de viajes está vacío'},
                status=400,
                origin=origin,
            )

        # ── 4. Validar y crear viajes ─────────────────────────────────────────
        created_trips     = []
        validation_errors = []
        TripModel         = env['ridery.trips'].sudo()

        for idx, trip_data in enumerate(trips_input):
            if not isinstance(trip_data, dict):
                validation_errors.append({
                    'index': idx,
                    'message': 'Cada viaje debe ser un objeto JSON',
                })
                continue

            vals, error_msg = _validate_trip(env, trip_data)

            if error_msg:
                validation_errors.append({'index': idx, 'message': error_msg})
                _logger.info("Ridery API: viaje[%d] rechazado — %s", idx, error_msg)
                continue

            try:
                trip = TripModel.create(vals)
                created_trips.append({'id': trip.id, 'name': trip.name})
                _logger.info(
                    "Ridery API: viaje creado id=%d name='%s'", trip.id, trip.name
                )
            except Exception as exc:
                validation_errors.append({'index': idx, 'message': str(exc)})
                _logger.exception("Ridery API: error al crear viaje[%d]", idx)

        # ── 5. Construir respuesta ────────────────────────────────────────────
        total_received = len(trips_input)
        total_created  = len(created_trips)

        if total_created == 0:
            status_label = 'error'
        elif total_created < total_received:
            status_label = 'partial'
        else:
            status_label = 'ok'

        response_data = {
            'status':   status_label,
            'received': total_received,
            'created':  total_created,
            'trips':    created_trips,
            'errors':   validation_errors,
        }

        http_status = 200 if status_label in ('ok', 'partial') else 422
        return _json_response(response_data, status=http_status, origin=origin)
