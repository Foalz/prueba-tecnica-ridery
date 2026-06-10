{
    'name': 'Viajes Ridery',
    'version': '16.0.0.0.0',
    'category': 'Operations/Transportation',
    'summary': 'Módulo principal para la gestión de conductores y reservas de viajes.',
    'description': """
        Core Business Logic para prueba técnica.
        - Gestión del modelo de Conductores (Drivers).
        - Gestión del modelo de Reservas (Bookings).
    """,
    'author': 'Pedro Contreras',
    'depends': [
        'base',
        'fleet', 
        'account'
    ],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',

        'data/sequence.xml',

        'views/ridery_trips.xml',
        'views/res_partner.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
