# -*- coding: utf-8 -*-
from odoo import fields, api, models, _


class RideryTrips(models.Model):
    _name = 'rider.trips'
    _description = 'Modelo dedicado a almacenar todos los viajes de la aplicacion'
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
    ]

    company_id = fields.Many2one(
        string="Company",
        comodel_name='res.company',
        default=lambda self: self.env.company.id,
        required=True,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
    )
    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehicle'
    )
    driver_id = fields.Many2one(
        related='vehicle_id.driver_id',
        string='Driver'
    )
    driver_license_plate = fields.Char(
        string='Driver license plate',
        related='vehicle_id.license_plate',
        index=True
    )
    distance = fields.Float(
        string='Distance',
        help="""
        Distance of the trip measured in kilometers
        """
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('in_progress', 'In Progress'),
            ('cancelled', 'Cancelled')
        ],
        tracking=True,
        default='draft'
    )
    price = fields.Monetary(
        string='Total',
        currency_field='company_id.currency_id',
    )
