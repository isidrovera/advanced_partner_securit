# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.http import request
import requests
import logging
import werkzeug
import json

_logger = logging.getLogger(__name__)

class TurnstileAuthSignup(AuthSignupHome):
    
    @http.route()
    def web_auth_signup(self, *args, **kw):
        """Sobrescribe el método de registro para validar Turnstile"""
        _logger.info("Procesando registro con validación Turnstile")
        
        # Configuración para Turnstile
        turnstile_secret = "0x4AAAAAAA-your_secret_key"  # Reemplazar con tu clave secreta
        turnstile_verify_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        
        # Obtener el token de la respuesta del captcha
        turnstile_response = kw.get('cf-turnstile-response')
        
        # Verificar si se está enviando un formulario (POST)
        if request.httprequest.method == 'POST':
            # Inicializar diccionario de errores si no existe
            if not kw.get('error'):
                kw['error'] = dict()
            
            # Validar aceptación de términos
            if kw.get('accept_terms') != 'on':
                kw['error']['terms'] = _("Debes aceptar los términos y condiciones para registrarte.")
                return super().web_auth_signup(*args, **kw)
            
            # Validar captcha Turnstile
            if not turnstile_response:
                _logger.warning("Intento de registro sin completar captcha")
                kw['error']['captcha'] = _("Por favor, completa el captcha correctamente.")
                return super().web_auth_signup(*args, **kw)
            
            # Verificar el token con la API de Cloudflare
            try:
                _logger.info("Verificando token Turnstile con Cloudflare")
                verification_data = {
                    'secret': turnstile_secret,
                    'response': turnstile_response,
                    'remoteip': request.httprequest.remote_addr
                }
                
                verification_response = requests.post(
                    turnstile_verify_url, 
                    data=verification_data,
                    timeout=5
                )
                
                result = verification_response.json()
                
                if not result.get('success', False):
                    _logger.warning(f"Verificación de Turnstile fallida: {result}")
                    kw['error']['captcha'] = _("Verificación de seguridad fallida. Por favor, inténtalo de nuevo.")
                    return super().web_auth_signup(*args, **kw)
                
                _logger.info("Verificación de Turnstile exitosa")
                
            except Exception as e:
                _logger.error(f"Error al verificar Turnstile: {str(e)}")
                kw['error']['captcha'] = _("Error al verificar la seguridad. Por favor, inténtalo de nuevo.")
                return super().web_auth_signup(*args, **kw)
        
        # Continuar con el flujo original de registro
        return super().web_auth_signup(*args, **kw)

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup_override(self, *args, **kw):
        """
        Sobrescribe la ruta de registro para asegurar que el captcha se valide
        """
        return self.web_auth_signup(*args, **kw)
        
    @http.route()
    def web_login(self, *args, **kw):
        """
        Mantiene el login original sin cambios (no requiere captcha)
        """
        return super().web_login(*args, **kw)
    
    @http.route()
    def web_reset_password(self, *args, **kw):
        """
        Mantiene el reset de contraseña original sin cambios
        """
        return super().web_reset_password(*args, **kw)

    # Método opcional para validar Turnstile mediante una ruta API
    @http.route('/auth_signup/verify_turnstile', type='json', auth='public', website=True, csrf=False)
    def verify_turnstile(self, token=None):
        """
        Endpoint para verificar el token de Turnstile mediante AJAX
        """
        if not token:
            return {'success': False, 'error': 'Token no proporcionado'}
            
        turnstile_secret = "0x4AAAAAAA-your_secret_key"  # Reemplazar con tu clave secreta
        turnstile_verify_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        
        try:
            verification_data = {
                'secret': turnstile_secret,
                'response': token,
                'remoteip': request.httprequest.remote_addr
            }
            
            verification_response = requests.post(
                turnstile_verify_url, 
                data=verification_data,
                timeout=5
            )
            
            result = verification_response.json()
            return result
            
        except Exception as e:
            _logger.error(f"Error al verificar Turnstile: {str(e)}")
            return {'success': False, 'error': str(e)}