{
    'name': 'Ridery - Localization',
    'version': '16.0.0.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Extensión de la Localización Venezolana con validaciones de identidad.',
    'description': """
        Extiende la localización venezolana base (l10n_ve) con:
        - Validación del campo RIF/Cédula según legislación venezolana.
        - Campo de identificación obligatorio para compañías con localización VE.
        - Formatos soportados: V-, E-, J-, G- seguidos de 7-9 dígitos.
    """,
    'author': 'Pedro Contreras',
    'depends': ['base', 'l10n_ve'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
