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
        - Protección contra bots con Cloudflare Turnstile
    """,
    'category': 'Contacts',
    'author': 'Tu Empresa',
    'website': 'https://www.tuempresa.com',
    'depends': ['base', 'web', 'mail', 'auth_signup'],
    'data': [
        'security/ir.model.access.csv',
        'views/ip_registration.xml',
        'data/system_parameters.xml',
        'views/partner_views.xml',        
        'views/signup_verification.xml',
        'data/mail_template_data.xml',
        'data/ir_cron.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            
        ],
    },
    # Permitir carga de recursos externos de Cloudflare para Turnstile
    'external_dependencies': {
        'python': [],
        'bin': []
    },
    # Dominios permitidos para cargar recursos externos
    'CSP': {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-eval'", "'unsafe-inline'", 
                      "challenges.cloudflare.com"],
        'style-src': ["'self'", "'unsafe-inline'"],
        'font-src': ["'self'"],
        'img-src': ["'self'", "data:", "challenges.cloudflare.com"],
        'connect-src': ["'self'", "challenges.cloudflare.com"],
        'frame-src': ["'self'", "challenges.cloudflare.com"]
    },
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}