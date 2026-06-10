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
        domain=[('ridery_role', '=', 'passenger')],
        required=True,
    )

    # ── Conductor ─────────────────────────────────────────────────────────────
    driver_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Conductor',
        domain=[('ridery_role', '=', 'driver')],
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

    # ── Viaje ─────────────────────────────────────────────────────────────────
    distance = fields.Float(
        string='Distancia (km)',
        help="Distancia total del viaje medida en kilómetros.",
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmado'),
            ('in_progress', 'En Progreso'),
            ('cancelled', 'Cancelado'),
        ],
        string='Estado',
        tracking=True,
        default='draft',
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

    # ── Secuencia ─────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('ridery.trips') or _('Nuevo')
                )
        return super().create(vals_list)
