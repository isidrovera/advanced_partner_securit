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
    email = fields.Char(string='Correo electrónico', required=True, index=True)
    create_date = fields.Datetime(string='Fecha de creación', readonly=True)
    state = fields.Selection([
        ('code_sent', 'Código Enviado'),
        ('registered', 'Usuario Registrado')
    ], string='Estado', default='registered', required=True, index=True)

class BlockedEmail(models.Model):
    """
    Modelo para mantener un registro de correos bloqueados por motivos de seguridad.
    """
    _name = 'auth_signup_security.blocked_email'
    _description = 'Correos bloqueados por motivos de seguridad'
    
    email = fields.Char(string='Correo electrónico', required=True, index=True)
    blocked_date = fields.Datetime(string='Fecha de bloqueo', default=lambda self: fields.Datetime.now())
    reason = fields.Char(string='Motivo de bloqueo', required=True)
    is_permanent = fields.Boolean(string='Bloqueo permanente', default=False,
                                help='Si es verdadero, el bloqueo no expira automáticamente')
    
    _sql_constraints = [
        ('email_unique', 'unique(email)', 'Este correo ya está registrado como bloqueado.')
    ]