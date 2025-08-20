# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.http import request
import re
import logging
import datetime

_logger = logging.getLogger(__name__)

class CustomResPartner(models.Model):
    _inherit = 'res.partner'
    
    has_license = fields.Boolean(string="Tiene licencia", default=False)
    registration_ip = fields.Char(string="IP de registro", readonly=True)
    registration_date = fields.Datetime(string="Fecha de registro", readonly=True)
    is_verified_email = fields.Boolean(string="Email verificado", default=False)

    
    
    @api.model
    def create(self, vals):
        # Obtener la IP del usuario directamente del objeto request
        if hasattr(request, 'httprequest'):
            vals['registration_ip'] = request.httprequest.remote_addr
            vals['registration_date'] = fields.Datetime.now()

        # Verificar que el email sea válido
        if vals.get('email'):
            if not self._is_valid_email(vals.get('email')):
                raise ValidationError(_("El correo electrónico no parece ser válido."))

            # Verificar que no sea un dominio de correo desechable
            if self._is_disposable_email(vals.get('email')):
                raise ValidationError(_("No se permiten correos electrónicos temporales o desechables."))

        return super(CustomResPartner, self).create(vals)

    
    def _is_valid_email(self, email):
        """Verificar si el formato del correo es válido usando regex"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_disposable_email(self, email):
        """Comprobar si el dominio es un proveedor de correo desechable"""
        domain = email.split('@')[-1].lower()
        disposable_domains = [
            'mailinator.com', 'yopmail.com', 'tempmail.com', 'guerrillamail.com', 
            'temp-mail.org', 'throwawaymail.com', '10minutemail.com', 'mailnesia.com',
            'trash-mail.com', 'getairmail.com', 'mailnull.com', 'spamgourmet.com',
            'sharklasers.com', 'spam4.me', 'dispostable.com', 'nada.email',
            'getnada.com', 'spamex.com', 'mytrashmail.com'
        ]
        return domain in disposable_domains
class ResUsers(models.Model):
    _inherit = 'res.users'
    
    @api.model
    def create(self, vals):
        """Sobreescribe create para agregar verificación de CAPTCHA si es necesario"""
        if not vals.get('captcha_verified', False):
            # Implementa aquí la lógica para verificar CAPTCHA
            # Esta es una implementación mock, deberías usar un servicio real como reCAPTCHA
            _logger.info("Se debería verificar CAPTCHA aquí")
            # vals['captcha_verified'] = True
        
        return super(ResUsers, self).create(vals)