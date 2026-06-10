# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    trip_passenger_count = fields.Integer(
        string='Viajes como Pasajero',
        compute='_compute_trip_counts',
    )

    trip_driver_count = fields.Integer(
        string='Viajes como Conductor',
        compute='_compute_trip_counts',
    )

    def _compute_trip_counts(self):
        for partner in self:
            partner.trip_passenger_count = self.env['ridery.trips'].search_count([
                ('partner_id', '=', partner.id),
            ])
            partner.trip_driver_count = self.env['ridery.trips'].search_count([
                ('driver_id', '=', partner.id),
            ])

    def action_view_trips_as_passenger(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Viajes como Pasajero',
            'view_mode': 'tree,form',
            'res_model': 'ridery.trips',
            'domain': [('partner_id', '=', self.id)],
            'context': {'create': False},
        }

    def action_view_trips_as_driver(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Viajes como Conductor',
            'view_mode': 'tree,form',
            'res_model': 'ridery.trips',
            'domain': [('driver_id', '=', self.id)],
            'context': {'create': False},
        }
