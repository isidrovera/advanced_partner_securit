# -*- coding: utf-8 -*-
from odoo import models, fields

class IpRegistration(models.Model):
    """
    Modelo para registrar las IPs que han creado cuentas.
    Se permite hasta 3 cuentas por IP por día.
    """
    _name = 'auth_signup_security.ip_registration'
    _description = 'Registro de IPs para creación de cuentas'

    ip_address = fields.Char(string='Dirección IP', required=True, index=True)
    email = fields.Char(string='Correo electrónico')
    create_date = fields.Datetime(string='Fecha de creación', readonly=True)

    _sql_constraints = [
        ('ip_date_limit',
         'CHECK ((SELECT COUNT(*) FROM auth_signup_security_ip_registration WHERE ip_address = NEW.ip_address AND create_date::date = CURRENT_DATE) < 3)',
         'Solo se permiten tres registros por IP al día.')
    ]
