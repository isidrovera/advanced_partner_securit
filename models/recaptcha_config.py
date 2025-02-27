# -*- coding: utf-8 -*-
# models/recaptcha_config.py

from odoo import models, fields, api

class RecaptchaConfig(models.Model):
    _name = 'auth_signup_security.recaptcha_config'
    _description = 'Configuración de reCAPTCHA'
    
    site_key = fields.Char(string='Clave del sitio', required=True)
    secret_key = fields.Char(string='Clave secreta', required=True)
    is_enabled = fields.Boolean(string='Habilitado', default=True)
    
    @api.model
    def get_config(self):
        """Obtiene la configuración activa de reCAPTCHA"""
        config = self.search([], limit=1)
        if not config:
            return None
        return config