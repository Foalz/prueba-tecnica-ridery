# -*- coding: utf-8 -*-
from odoo import fields, api, models, _


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
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Pasajero',
    )
    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehículo'
    )
    driver_id = fields.Many2one(
        related='vehicle_id.driver_id',
        string='Conductor'
    )
    driver_license_plate = fields.Char(
        string='Placa',
        related='vehicle_id.license_plate',
        index=True
    )
    distance = fields.Float(
        string='Distancia (km)',
        help="""
        Distancia total del viaje medida en kilómetros.
        """
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('confirmed', 'Confirmado'),
            ('in_progress', 'En Progreso'),
            ('cancelled', 'Cancelado')
        ],
        string='Estado',
        tracking=True,
        default='draft'
    )
    price = fields.Monetary(
        string='Total de la Carrera',
        currency_field='currency_id',
        tracking=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nuevo')) == _('Nuevo'):
                vals['name'] = self.env['ir.sequence'].next_by_code('ridery.trips') or _('Nuevo')
        return super().create(vals_list)
