# -*- coding: utf-8 -*-
import logging
import requests
from odoo import http, _
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

    @http.route('/web/signup', type='http', auth='public', website=True)
    def web_auth_signup(self, *args, **kw):
        """Validar Turnstile antes de procesar el registro"""
        qcontext = self.get_auth_signup_qcontext()

        # Asegurar que 'error' existe en qcontext
        if 'error' not in qcontext:
            qcontext['error'] = {}

        turnstile_response = kw.get('cf-turnstile-response')

        if not self.validate_turnstile(turnstile_response):
            _logger.warning("[Turnstile] Captcha no válido, bloqueando registro.")
            qcontext['error']['captcha'] = _("Por favor, completa el captcha correctamente.")
            return request.render('auth_signup.signup', qcontext)

        _logger.info("[Turnstile] Captcha validado correctamente. Procesando registro de usuario...")

        return super(AuthSignupExtended, self).web_auth_signup(*args, **kw)
