# -*- coding: utf-8 -*-
{
    'name': 'Seguridad Avanzada de Contactos',
    'version': '1.0',
    'summary': 'Implementa seguridad avanzada para contactos: prevención de duplicados, verificación de correo y protección anti-bots',
    'description': """
        Este módulo extiende el modelo res.partner añadiendo:
        - Campo de licencia
        - Restricciones de registro (1 por IP por día)
        - Verificación de correo electrónico
        - Protección contra bots
    """,
    'category': 'Contacts',
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': ['base', 'web', 'mail', 'auth_signup'],
    'data': [
        'security/ir.model.access.csv',
        'views/partner_views.xml',
        'views/auth_signup_templates.xml',
        'data/mail_templates.xml',
        'data/ir_cron.xml',
    ],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}