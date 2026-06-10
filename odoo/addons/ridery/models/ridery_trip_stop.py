# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class RideryTripStop(models.Model):
    _name = 'ridery.trip.stop'
    _description = 'Parada de Viaje Ridery'
    _order = 'stop_type_order, sequence, id'

    trip_id = fields.Many2one(
        comodel_name='ridery.trips',
        string='Viaje',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(
        string='Dirección',
        required=True,
    )
    stop_type = fields.Selection(
        selection=[
            ('start', 'Inicio'),
            ('intermediate', 'Intermedia'),
            ('end', 'Fin'),
        ],
        string='Tipo de Parada',
        required=True,
        default='intermediate',
    )
    latitude = fields.Float(
        string='Latitud',
        digits=(10, 7),
    )
    longitude = fields.Float(
        string='Longitud',
        digits=(10, 7),
    )
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
    )
    stop_type_order = fields.Integer(
        string='Orden por Tipo',
        compute='_compute_stop_type_order',
        store=True,
    )

    @api.depends('stop_type')
    def _compute_stop_type_order(self):
        for record in self:
            if record.stop_type == 'start':
                record.stop_type_order = 1
            elif record.stop_type == 'end':
                record.stop_type_order = 3
            else:
                record.stop_type_order = 2

    @api.constrains('stop_type', 'trip_id')
    def _check_stop_types(self):
        for record in self:
            if record.stop_type in ['start', 'end']:
                # Contar cuántas paradas del mismo tipo tiene el viaje actual
                count = self.search_count([
                    ('trip_id', '=', record.trip_id.id),
                    ('stop_type', '=', record.stop_type),
                ])
                if count > 1:
                    tipo = 'Inicio' if record.stop_type == 'start' else 'Fin'
                    raise ValidationError(_("Un viaje no puede tener más de una parada de tipo '%s'.") % tipo)
