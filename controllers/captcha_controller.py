# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import json
import logging
import requests

_logger = logging.getLogger(__name__)

class CaptchaController(http.Controller):
    @http.route('/web/captcha/verify', type='json', auth='public')
    def verify_captcha(self, **kw):
        """Verifica el token reCAPTCHA enviado desde el cliente"""
        token = kw.get('token')
        if not token:
            return {'success': False, 'error': 'No se proporcionó un token de CAPTCHA'}
        
        try:
            # Reemplaza esto con tu clave secreta de reCAPTCHA
            secret_key = request.env['ir.config_parameter'].sudo().get_param('recaptcha.secret_key')
            if not secret_key:
                _logger.warning("reCAPTCHA secret_key no configurada")
                return {'success': False, 'error': 'reCAPTCHA no configurado'}
            
            # Verificar el token con la API de Google
            response = requests.post(
                'https://www.google.com/recaptcha/api/siteverify',
                data={
                    'secret': secret_key,
                    'response': token,
                    'remoteip': request.httprequest.remote_addr
                }
            )
            result = response.json()
            
            if result.get('success'):
                return {'success': True}
            else:
                _logger.warning("Verificación de CAPTCHA fallida: %s", result.get('error-codes'))
                return {'success': False, 'error': 'Verificación de CAPTCHA fallida'}
        
        except Exception as e:
            _logger.exception("Error durante la verificación de CAPTCHA: %s", str(e))
            return {'success': False, 'error': str(e)}

class AuthSignupHome(http.Controller):
    @http.route('/web/signup', type='http', auth='public', website=True)
    def web_auth_signup(self, *args, **kw):
        """Sobreescribe el método de registro para incluir CAPTCHA"""
        # Aquí implementarás la lógica para añadir el CAPTCHA en la página de registro
        # Esto requiere modificar la plantilla de registro, que podría hacerse con un QWeb heredado
        
        # Esta es una implementación básica que deberías ampliar
        return request.render('web.signup', {'captcha_site_key': request.env['ir.config_parameter'].sudo().get_param('recaptcha.site_key')})