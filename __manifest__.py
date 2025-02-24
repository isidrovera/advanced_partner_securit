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
    'assets': {
        'web.assets_frontend': [
            'advanced_partner_securit/static/src/js/recaptcha.js',
        ],
    },
    # Permitir carga de recursos externos de Google para reCAPTCHA
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    # Dominios permitidos para cargar recursos externos
    'CSP': {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-eval'", "'unsafe-inline'", 
                      "www.google.com", "www.gstatic.com", "*.googleapis.com"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'font-src': ["'self'"],
        'img-src': ["'self'", "data:", "www.google.com", "www.gstatic.com"],
        'connect-src': ["'self'"],
        'frame-src': ["'self'", "www.google.com"]
    },
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}