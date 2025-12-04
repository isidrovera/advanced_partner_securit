# -*- coding: utf-8 -*-
from odoo import models, fields

class RecaptchaConfig(models.Model):
    _name = 'auth_signup_security.recaptcha_config'
    _description = 'Configuración de reCAPTCHA para registro'

    name = fields.Char(string="Nombre", default="Configuración reCAPTCHA", required=True)
    site_key = fields.Char(string="Site Key", required=True)
    secret_key = fields.Char(string="Secret Key", required=True)
    is_enabled = fields.Boolean(string="Activado", default=True)

    # Útil si quieres tener varios registros pero solo uno activo
    active = fields.Boolean(string="Activo", default=True)

    def get_config(self):
        """Devuelve el registro activo a usar por el controlador"""
        config = self.search([('active', '=', True)], limit=1)
        return config
