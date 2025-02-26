# -*- coding: utf-8 -*-
from odoo import models, fields, api

class IpRegistration(models.Model):
    """
    Modelo para registrar las IPs que han creado cuentas
    Limita a una cuenta por IP por día
    """
    _name = 'auth_signup_security.ip_registration'
    _description = 'Registro de IPs para creación de cuentas'
    
    ip_address = fields.Char(string='Dirección IP', required=True, index=True)
    email = fields.Char(string='Correo electrónico')
    create_date = fields.Datetime(string='Fecha de creación', readonly=True)
    
    _sql_constraints = [
        ('ip_date_uniq', 
         'unique(ip_address, create_date)', 
         'Ya se ha registrado una cuenta desde esta IP hoy')
    ]