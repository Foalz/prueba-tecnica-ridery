# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# Formatos válidos de RIF/Cédula venezolana:
# Personas naturales:  V-12345678  o  E-12345678  (7-8 dígitos)
# Personas jurídicas:  J-123456789              (9 dígitos)
# Gubernamental:       G-12345678               (8 dígitos)
VE_VAT_REGEX = re.compile(
    r'^[VvEeJjGgPp]-?\d{7,9}$'
)

VE_COUNTRY_CODE = 'VE'

# Campos que, si cambian, pueden afectar la validación venezolana
VE_TRIGGER_FIELDS = {'vat', 'country_id'}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_ve_localization = fields.Boolean(
        string='Localización Venezolana',
        compute='_compute_is_ve_localization',
    )
    vat = fields.Char(
        string='RIF / Cédula',
        required=True,
        index=True,
    )

    @api.depends('company_id', 'company_id.country_id')
    def _compute_is_ve_localization(self):
        for partner in self:
            company = partner.company_id or self.env.company
            partner.is_ve_localization = (
                company.country_id.code == VE_COUNTRY_CODE
            )

    def _validate_ve_vat(self):
        """
        Valida el RIF/Cédula venezolano para todos los partners en self.
        Solo aplica si la compañía asociada usa localización venezolana (VE).
        """
        for partner in self:
            company = partner.company_id or self.env.company
            if company.country_id.code != VE_COUNTRY_CODE:
                continue

            if not partner.vat:
                raise ValidationError(_(
                    "El campo RIF/Cédula es obligatorio para la localización "
                    "venezolana. Por favor ingrese el documento de identidad "
                    "del contacto '%(name)s'.",
                    name=partner.name or '',
                ))

            vat_clean = partner.vat.strip().upper().replace(' ', '')
            if not VE_VAT_REGEX.match(vat_clean):
                raise ValidationError(_(
                    "El RIF/Cédula '%(vat)s' del contacto '%(name)s' no tiene "
                    "un formato venezolano válido.\n\n"
                    "Formatos aceptados:\n"
                    "  • Persona natural:   V-12345678  o  E-12345678\n"
                    "  • Persona jurídica:  J-123456789\n"
                    "  • Gubernamental:     G-12345678\n\n"
                    "El prefijo (V, E, J, G) seguido de guión y los dígitos.",
                    vat=partner.vat,
                    name=partner.name or '',
                ))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._validate_ve_vat()
        return records

    def write(self, vals):
        result = super().write(vals)
        if VE_TRIGGER_FIELDS & vals.keys():
            self._validate_ve_vat()
        return result
