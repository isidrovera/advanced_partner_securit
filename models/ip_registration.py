# -*- coding: utf-8 -*-
from odoo import models, fields

class IpRegistration(models.Model):
    """
    Modelo para registrar las IPs que han solicitado códigos o creado cuentas.
    Se permite hasta 3 cuentas por IP por día y solo un código por IP por día.
    """
    _name = 'auth_signup_security.ip_registration'
    _description = 'Registro de IPs para solicitud de código y creación de cuentas'

    ip_address = fields.Char(string='Dirección IP', required=True, index=True)
    email = fields.Char(string='Correo electrónico')
    create_date = fields.Datetime(string='Fecha de creación', readonly=True)
    state = fields.Selection([
        ('code_sent', 'Código Enviado'),
        ('registered', 'Usuario Registrado')
    ], string='Estado', default='registered', required=True, index=True)
