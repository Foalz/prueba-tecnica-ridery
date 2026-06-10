# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# Valores de estado válidos para ridery.trips
VALID_STATES = {'draft', 'confirmed', 'in_progress', 'cancelled'}

# Headers CORS que se añaden a toda respuesta del endpoint
_CORS_HEADERS_BASE = {
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-API-Key',
    'Access-Control-Max-Age': '86400',
}


def _get_param(env, key, default=''):
    """Lee un ir.config_parameter de forma segura."""
    return env['ir.config_parameter'].sudo().get_param(key, default)


def _json_response(data, status=200, origin=None):
    """Construye una Response JSON con los headers CORS correctos."""
    headers = {'Content-Type': 'application/json'}
    if origin:
        headers['Access-Control-Allow-Origin'] = origin
    headers.update(_CORS_HEADERS_BASE)
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status,
        headers=list(headers.items()),
    )


def _validate_trip(env, index, trip_data):
    """
    Valida los datos de un único viaje.

    Retorna (vals_dict, None) si es válido,
    o (None, error_message_str) si hay errores.
    """
    errors = []

    # ── Campos requeridos ─────────────────────────────────────────────────────
    required_fields = ['partner_id', 'driver_partner_id', 'distance', 'price']
    for field in required_fields:
        if field not in trip_data or trip_data[field] is None:
            errors.append(f"Campo requerido ausente: '{field}'")

    if errors:
        return None, '; '.join(errors)

    partner_id = trip_data['partner_id']
    driver_partner_id = trip_data['driver_partner_id']

    # ── Tipos numéricos ───────────────────────────────────────────────────────
    try:
        distance = float(trip_data['distance'])
        price = float(trip_data['price'])
    except (TypeError, ValueError):
        return None, "'distance' y 'price' deben ser numéricos"

    if distance <= 0:
        errors.append("'distance' debe ser mayor que 0")
    if price < 0:
        errors.append("'price' no puede ser negativo")

    # ── Validar partner (pasajero) ────────────────────────────────────────────
    if not isinstance(partner_id, int):
        errors.append("'partner_id' debe ser un entero")
    else:
        passenger = env['res.partner'].sudo().browse(partner_id)
        if not passenger.exists():
            errors.append(f"El contacto con id={partner_id} no existe")
        elif passenger.ridery_role != 'passenger':
            errors.append(
                f"El contacto id={partner_id} ({passenger.name}) "
                f"no tiene rol 'Pasajero' (rol actual: {passenger.ridery_role})"
            )

    # ── Validar driver_partner (conductor) ────────────────────────────────────
    if not isinstance(driver_partner_id, int):
        errors.append("'driver_partner_id' debe ser un entero")
    else:
        driver = env['res.partner'].sudo().browse(driver_partner_id)
        if not driver.exists():
            errors.append(f"El contacto con id={driver_partner_id} no existe")
        elif driver.ridery_role != 'driver':
            errors.append(
                f"El contacto id={driver_partner_id} ({driver.name}) "
                f"no tiene rol 'Conductor' (rol actual: {driver.ridery_role})"
            )

    # ── Pasajero != Conductor ─────────────────────────────────────────────────
    if (
        isinstance(partner_id, int)
        and isinstance(driver_partner_id, int)
        and partner_id == driver_partner_id
    ):
        errors.append("El pasajero y el conductor no pueden ser la misma persona")

    if errors:
        return None, '; '.join(errors)

    # ── state (opcional) ──────────────────────────────────────────────────────
    state = trip_data.get('state', 'draft')
    if state not in VALID_STATES:
        return None, f"'state' inválido: '{state}'. Valores permitidos: {sorted(VALID_STATES)}"

    # ── company_id (opcional) ─────────────────────────────────────────────────
    vals = {
        'partner_id': partner_id,
        'driver_partner_id': driver_partner_id,
        'distance': distance,
        'price': price,
        'state': state,
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


class RideryTripsApiController(http.Controller):

    @http.route(
        '/ridery/api/v1/trips',
        type='http',
        auth='none',          # La autenticación se maneja manualmente con API Key
        methods=['POST', 'OPTIONS'],
        csrf=False,
        cors=None,            # CORS manual para control total
        save_session=False,
    )
    def receive_trips(self, **kwargs):
        """
        Recibe un JSON de viajes (objeto o array) y los registra en ridery.trips.

        Headers requeridos:
            Origin:    debe coincidir con ridery.allowed_origin
            X-API-Key: debe coincidir con ridery.api_key
        """
        env = request.env

        # ── Leer configuración ────────────────────────────────────────────────
        allowed_origin = _get_param(env, 'ridery.allowed_origin', '').strip()
        api_key_stored = _get_param(env, 'ridery.api_key', '').strip()

        origin = request.httprequest.headers.get('Origin', '').strip()

        # ── Preflight OPTIONS ─────────────────────────────────────────────────
        if request.httprequest.method == 'OPTIONS':
            if allowed_origin and origin != allowed_origin:
                return Response('Forbidden', status=403)
            return _json_response({}, status=204, origin=origin or allowed_origin)

        # ── 1. Validar CORS (Origin) ──────────────────────────────────────────
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
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, Exception) as exc:
            return _json_response(
                {'status': 'error', 'message': f'JSON inválido: {exc}'},
                status=400,
                origin=origin,
            )

        # Aceptar tanto objeto {} como array [{}]
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
        created_trips = []
        validation_errors = []

        TripModel = env['ridery.trips'].sudo()

        for idx, trip_data in enumerate(trips_input):
            if not isinstance(trip_data, dict):
                validation_errors.append({
                    'index': idx,
                    'message': 'Cada viaje debe ser un objeto JSON',
                })
                continue

            vals, error_msg = _validate_trip(env, idx, trip_data)

            if error_msg:
                validation_errors.append({'index': idx, 'message': error_msg})
                _logger.info("Ridery API: viaje[%d] rechazado — %s", idx, error_msg)
                continue

            try:
                trip = TripModel.create(vals)
                created_trips.append({'id': trip.id, 'name': trip.name})
                _logger.info("Ridery API: viaje creado id=%d name='%s'", trip.id, trip.name)
            except Exception as exc:
                validation_errors.append({'index': idx, 'message': str(exc)})
                _logger.exception("Ridery API: error al crear viaje[%d]", idx)

        # ── 5. Construir respuesta ────────────────────────────────────────────
        total_received = len(trips_input)
        total_created = len(created_trips)

        if total_created == 0:
            status_label = 'error'
        elif total_created < total_received:
            status_label = 'partial'
        else:
            status_label = 'ok'

        response_data = {
            'status': status_label,
            'received': total_received,
            'created': total_created,
            'trips': created_trips,
            'errors': validation_errors,
        }

        http_status = 200 if status_label in ('ok', 'partial') else 422
        return _json_response(response_data, status=http_status, origin=origin)
