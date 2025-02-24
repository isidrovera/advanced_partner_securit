# -*- coding: utf-8 -*-
import logging
import requests
import random
import string
from datetime import datetime, timedelta

from odoo import http, _, fields
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.http import request

_logger = logging.getLogger(__name__)

class AuthSignupExtended(AuthSignupHome):

    def validate_turnstile(self, response):
        """Verificar respuesta de Turnstile con Cloudflare"""
        if not response:
            _logger.warning("[Turnstile] No se recibió respuesta del captcha.")
            return False

        secret_key = request.env['ir.config_parameter'].sudo().get_param('turnstile.secret_key', '')
        if not secret_key:
            _logger.warning("[Turnstile] Clave secreta no configurada en Odoo.")
            return True  # Si no está configurada, no se bloquea el registro

        try:
            _logger.info("[Turnstile] Validando token en Cloudflare...")

            result = requests.post(
                'https://challenges.cloudflare.com/turnstile/v0/siteverify',
                data={'secret': secret_key, 'response': response, 'remoteip': request.httprequest.remote_addr},
                timeout=5
            ).json()

            if result.get('success'):
                _logger.info("[Turnstile] Validación exitosa para IP: %s", request.httprequest.remote_addr)
                return True
            else:
                _logger.error("[Turnstile] Validación fallida. Respuesta: %s", result)
                return False
        except Exception as e:
            _logger.exception("[Turnstile] Error en la validación del captcha: %s", str(e))
            return False

    def validate_ip_restriction(self):
        """Verificar si esta IP ya ha registrado demasiadas cuentas hoy"""
        ip_address = request.httprequest.remote_addr
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59)

        count = request.env['res.partner'].sudo().search_count([
            ('registration_ip', '=', ip_address),
            ('registration_date', '>=', today_start),
            ('registration_date', '<=', today_end),
        ])

        if count >= 3:
            _logger.warning("[Registro] IP %s ha excedido el límite de registros diarios.", ip_address)
        
        return count < 3

    def validate_email_domain(self, email):
        """Validar que el dominio de correo esté permitido"""
        if not email:
            return False

        domain = email.split('@')[-1].lower()
        blocked_domains = [
            'mailinator.com', 'yopmail.com', 'tempmail.com', '10minutemail.com', 
            'nada.email', 'getnada.com', 'throwawaymail.com'
        ]

        if domain in blocked_domains:
            _logger.warning("[Registro] Correo con dominio bloqueado: %s", domain)

        return domain not in blocked_domains

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        """Validar Turnstile y restricciones adicionales antes de procesar el registro"""
        qcontext = self.get_auth_signup_qcontext()

        email = qcontext.get('login', '')
        turnstile_response = kw.get('cf-turnstile-response')

        # Validación de Turnstile
        if not self.validate_turnstile(turnstile_response):
            _logger.warning("[Turnstile] Captcha no válido, bloqueando registro.")
            qcontext['error']['captcha'] = _("Por favor, completa el captcha correctamente.")

        # Validación de IP
        if not self.validate_ip_restriction():
            _logger.warning("[Registro] IP restringida por demasiados intentos.")
            qcontext['error']['ip'] = _("Has excedido el límite de registros desde esta IP hoy.")

        # Validación de dominio de correo
        if not self.validate_email_domain(email):
            _logger.warning("[Registro] Email con dominio bloqueado: %s", email)
            qcontext['error']['email'] = _("El dominio de este correo no está permitido.")

        # Si hay errores, mostrar formulario con errores
        if qcontext.get('error'):
            return request.render('auth_signup.signup', qcontext)

        _logger.info("[Registro] Usuario %s aprobado para registro.", email)
        return super(AuthSignupExtended, self).web_auth_signup(*args, **kw)
