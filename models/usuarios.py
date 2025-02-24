# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta

class UserVerification(models.Model):
    _name = 'user.verification'
    _description = 'User Email Verification'
    
    login = fields.Char('Email', required=True)
    name = fields.Char('Name', required=True)
    password = fields.Char('Password', required=True)
    verification_code = fields.Char('Verification Code', required=True)
    verification_token = fields.Char('Verification Token', required=True)
    expiration = fields.Datetime('Expiration Time', required=True)
    ip_address = fields.Char('IP Address')
    used = fields.Boolean('Used', default=False)
    
    @api.model
    def _gc_verification(self):
        """Garbage collect expired verification codes"""
        expired = self.search([
            '|',
            ('expiration', '<', fields.Datetime.now()),
            ('used', '=', True),
            ('create_date', '<', fields.Datetime.now() - timedelta(days=1))
        ])
        expired.unlink()
        return True