# -*- coding: utf-8 -*-
# controllers/captcha_controller.py

from odoo import http, _
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.http import request
import requests
import logging

_logger = logging.getLogger(__name__)


class SecurityAuthSignup(AuthSignupHome):
    """
    Registro con SOLO validación de reCAPTCHA.
    Si el captcha está ok, se usa el flujo estándar de Odoo.
    """

    def get_client_ip(self):
        """
        Obtiene la IP real del cliente (detrás de proxies, etc.)
        """
        request_obj = request.httprequest

        ip_headers = [
            'X-Forwarded-For',
            'X-Real-IP',
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_CLIENT_IP',
            'REMOTE_ADDR',
        ]

        client_ip = None
        for header in ip_headers:
            if header in request_obj.headers:
                ips = request_obj.headers.get(header, '').split(',')
                if ips:
                    client_ip = ips[0].strip()
                    break

        if not client_ip:
            client_ip = request_obj.remote_addr

        return client_ip

    def get_auth_signup_qcontext(self):
        """
        Contexto estándar de Odoo, solo nos aseguramos de que 'providers' exista.
        """
        qcontext = super(SecurityAuthSignup, self).get_auth_signup_qcontext()

        if 'providers' not in qcontext or qcontext['providers'] is None:
            qcontext['providers'] = []

        return qcontext

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        """
        Sobrescribe solo para meter la validación de reCAPTCHA.
        Si pasa, se llama a super() y Odoo hace el registro normal.
        """
        qcontext = self.get_auth_signup_qcontext()

        # Solo validamos en POST (cuando envían el formulario)
        if request.httprequest.method == 'POST':
            ip = self.get_client_ip()
            _logger.info(f"Intento de registro desde IP: {ip}")

            # Leer respuesta del captcha
            recaptcha_response = kw.get('g-recaptcha-response')

            # Leer configuración desde el modelo que ya tienes
            RecaptchaConfig = request.env['auth_signup_security.recaptcha_config'].sudo().get_config()
            recaptcha_enabled = RecaptchaConfig and RecaptchaConfig.is_enabled

            if recaptcha_enabled:
                # Si está habilitado, es obligatorio
                if not recaptcha_response:
                    _logger.warning(f"No se recibió respuesta de reCAPTCHA desde IP: {ip}")
                    qcontext['error'] = _("Por favor, complete la verificación de reCAPTCHA.")
                    return request.render('auth_signup.signup', qcontext)

                if not self._validate_recaptcha(recaptcha_response):
                    _logger.warning(f"Validación de reCAPTCHA fallida para IP: {ip}")
                    qcontext['error'] = _("Por favor, complete la verificación de reCAPTCHA.")
                    return request.render('auth_signup.signup', qcontext)

            # Si no está habilitado o si pasó la validación, seguimos con el flujo normal
            return super(SecurityAuthSignup, self).web_auth_signup(*args, **kw)

        # Para GET, solo mostrar el formulario estándar
        return request.render('auth_signup.signup', qcontext)

    def _validate_recaptcha(self, response):
        """
        Valida la respuesta del reCAPTCHA frente a Google.
        Usa tu modelo auth_signup_security.recaptcha_config.
        """
        if not response:
            return False

        RecaptchaConfig = request.env['auth_signup_security.recaptcha_config'].sudo()
        config = RecaptchaConfig.get_config()

        # Si por alguna razón no está configurado, lo tomamos como válido
        if not config or not config.is_enabled:
            _logger.info("reCAPTCHA no está configurado o está deshabilitado")
            return True

        try:
            ip = self.get_client_ip()
            data = {
                'secret': config.secret_key,
                'response': response,
                'remoteip': ip,
            }

            resp = requests.post(
                'https://www.google.com/recaptcha/api/siteverify',
                data=data,
                timeout=5
            )

            if resp.status_code == 200:
                result = resp.json()
                if result.get('success', False):
                    _logger.info(f"Validación reCAPTCHA exitosa para IP: {ip}")
                    return True
                else:
                    _logger.warning(
                        f"Validación reCAPTCHA fallida para IP: {ip}, errores: {result.get('error-codes')}"
                    )
                    return False
            else:
                _logger.error(f"Error HTTP al contactar reCAPTCHA: {resp.status_code}")
                return False

        except Exception as e:
            _logger.error(f"Error en validación reCAPTCHA: {str(e)}", exc_info=True)
            # Si falla la comunicación, por seguridad lo consideramos inválido
            return False
