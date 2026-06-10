# -*- coding: utf-8 -*-
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError


class RideryTrips(models.Model):
    _name = 'ridery.trips'
    _description = 'Modelo dedicado a almacenar todos los viajes de la aplicación'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
    ]

    name = fields.Char(
        string="Correlativo",
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('Nuevo'),
    )
    company_id = fields.Many2one(
        string="Compañía",
        comodel_name='res.company',
        default=lambda self: self.env.company.id,
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
        string='Moneda',
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Factura',
    )

    # ── Pasajero ──────────────────────────────────────────────────────────────
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Pasajero',
        required=True,
    )

    # ── Conductor ─────────────────────────────────────────────────────────────
    driver_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Conductor',
        domain=[('is_ridery_driver', '=', True)],
        required=True,
        tracking=True,
    )

    # ── Vehículo (derivado del conductor) ─────────────────────────────────────
    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehículo',
        compute='_compute_vehicle_from_driver',
        store=True,
        readonly=True,
    )
    driver_license_plate = fields.Char(
        string='Placa',
        related='vehicle_id.license_plate',
        index=True,
        store=True,
    )
    fleet_category_id = fields.Many2one(
        comodel_name='fleet.vehicle.model.category',
        string='Tipo de Flota',
        related='vehicle_id.category_id',
        store=True,
        readonly=True,
    )

    # ── Viaje ─────────────────────────────────────────────────────────────────
    stop_ids = fields.One2many(
        comodel_name='ridery.trip.stop',
        inverse_name='trip_id',
        string='Paradas',
        help='Listado de paradas del viaje (Inicio, Intermedias, Fin)',
    )

    @api.constrains('stop_ids')
    def _check_stops_requirements(self):
        for trip in self:
            starts = trip.stop_ids.filtered(lambda s: s.stop_type == 'start')
            ends = trip.stop_ids.filtered(lambda s: s.stop_type == 'end')
            
            if len(starts) != 1:
                raise ValidationError(_("El viaje debe tener exactamente una parada de tipo 'Inicio'."))
            if len(ends) != 1:
                raise ValidationError(_("El viaje debe tener exactamente una parada de tipo 'Fin'."))

    distance = fields.Float(
        string='Distancia (km)',
        help="Distancia total del viaje medida en kilómetros.",
    )
    state = fields.Selection(
        selection=[
            ('in_progress', 'En Progreso'),
            ('done', 'Finalizado'),
            ('cancelled', 'Cancelado'),
        ],
        string='Estado',
        tracking=True,
        default='in_progress',
    )
    price = fields.Monetary(
        string='Total de la Carrera',
        currency_field='currency_id',
        tracking=True,
    )

    # ── Compute ───────────────────────────────────────────────────────────────

    @api.depends('driver_partner_id')
    def _compute_vehicle_from_driver(self):
        """Busca el vehículo asignado al conductor en fleet.vehicle."""
        Vehicle = self.env['fleet.vehicle']
        for trip in self:
            if trip.driver_partner_id:
                vehicle = Vehicle.search(
                    [('driver_id', '=', trip.driver_partner_id.id)],
                    limit=1,
                )
                trip.vehicle_id = vehicle or False
            else:
                trip.vehicle_id = False

    # ── Constrains ────────────────────────────────────────────────────────────

    @api.constrains('partner_id', 'driver_partner_id')
    def _check_passenger_not_driver(self):
        for trip in self:
            if (
                trip.partner_id
                and trip.driver_partner_id
                and trip.partner_id == trip.driver_partner_id
            ):
                raise ValidationError(
                    _("El pasajero y el conductor no pueden ser la misma persona (%s).")
                    % trip.partner_id.name
                )

    @api.constrains('distance', 'price')
    def _check_positive_distance_price(self):
        for trip in self:
            if trip.distance <= 0:
                raise ValidationError(_("La distancia recorrida (km) debe ser mayor a 0."))
            if trip.price <= 0:
                raise ValidationError(_("El precio de la carrera debe ser mayor a 0."))

    # ── Secuencia ─────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('ridery.trips') or _('Nuevo')
                )
        return super().create(vals_list)

    # ── Facturación ───────────────────────────────────────────────────────────

    def action_create_invoice(self):
        """Crea una factura para el viaje actual basado en la ciudad y tipo de flota"""
        for trip in self:
            if trip.move_id:
                raise ValidationError(_("El viaje %s ya tiene una factura asignada.") % trip.name)
            if not trip.partner_id:
                raise ValidationError(_("El viaje debe tener un pasajero asignado para poder facturar."))
            
            # Buscamos el diario de ventas estándar
            journal = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', trip.company_id.id)], limit=1)
            if not journal:
                raise ValidationError(_("No hay ningún diario de ventas configurado en la compañía."))

            # Buscamos el producto pre-creado vía XML
            product = self.env.ref('ridery.product_ridery_trip', raise_if_not_found=False)
            if not product:
                raise ValidationError(_("El producto 'Servicio de Transporte Ridery' no está configurado en el sistema."))

            # 2. Crear la factura (account.move)
            move_vals = {
                'move_type': 'out_invoice',
                'partner_id': trip.partner_id.id,
                'journal_id': journal.id,
                'currency_id': trip.currency_id.id,
                'company_id': trip.company_id.id,
                'invoice_origin': trip.name,
                'invoice_line_ids': [(0, 0, {
                    'product_id': product.id,
                    'name': f'Servicio de Transporte Ridery - {trip.fleet_category_id.name or "Estándar"}',
                    'quantity': 1.0,
                    'price_unit': trip.price,
                })],
            }
            
            new_move = self.env['account.move'].create(move_vals)

            if new_move:
                new_move.action_post()
                
            trip.move_id = new_move.id

    @api.model
    def cron_invoice_trips(self):
        """Cron job para facturar por lotes viajes en progreso o confirmados que no tengan factura"""
        trips_to_invoice = self.search([
            ('move_id', '=', False),
            ('state', 'in', ['in_progress', 'done'])
        ], limit=100) # Lote de 100 para no agotar la memoria
        
        if trips_to_invoice:
            trips_to_invoice.action_create_invoice()

