# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
import requests
import logging
from odoo.http import request

_logger = logging.getLogger(__name__)
class TurnstileAuthSignup(AuthSignupHome):
    """
    Sobrescribe el controlador de registro original para añadir CSP y validación de Turnstile
    """
    
    def _add_csp_headers(self, response):
        """Agrega encabezados CSP a la respuesta si es necesario"""
        if hasattr(response, 'headers'):
            # Quitar cualquier CSP existente para evitar conflictos
            if 'Content-Security-Policy' in response.headers:
                del response.headers['Content-Security-Policy']
            
            # CSP permisivo pero específico para Cloudflare Turnstile
            csp = "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; " + \
                "script-src * 'unsafe-inline' 'unsafe-eval'; " + \
                "connect-src * 'unsafe-inline'; " + \
                "img-src * data: blob: 'unsafe-inline'; " + \
                "frame-src *; " + \
                "style-src * 'unsafe-inline'; " + \
                "font-src * data:"
            
            response.headers['Content-Security-Policy'] = csp
            _logger.info("CSP permisivo agregado para Turnstile")
        return response
        
    def get_auth_signup_qcontext(self):
        """Sobrescribe para asegurar que providers siempre esté definido"""
        qcontext = super(TurnstileAuthSignup, self).get_auth_signup_qcontext()
        
        # Asegurarse de que providers esté definido
        if 'providers' not in qcontext or qcontext['providers'] is None:
            qcontext['providers'] = []
        
        return qcontext
    
    @http.route()
    def web_auth_signup(self, *args, **kw):
        """Sobrescribe el método de registro para validar Turnstile y ajustar CSP"""
        _logger.info("Procesando registro con validación Turnstile")
        
        # Obtener la clave secreta
        ICP = request.env['ir.config_parameter'].sudo()
        turnstile_secret = ICP.get_param('website.turnstile_secret_key', 
                                         default="0x4AAAAAAA-your_secret_key")
        turnstile_verify_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        
        # Obtener el token de la respuesta del captcha
        turnstile_response = kw.get('cf-turnstile-response')
        
        # Verificar si se está enviando un formulario (POST)
        if request.httprequest.method == 'POST':
            # Inicializar el diccionario de errores
            qcontext = self.get_auth_signup_qcontext()
            error = {}
            
            # Validar aceptación de términos
            if not kw.get('accept_terms'):
                error['terms'] = _("Debes aceptar los términos y condiciones para registrarte.")
            
            # Validar captcha Turnstile
            if not turnstile_response:
                _logger.warning("Intento de registro sin completar captcha")
                error['captcha'] = _("Por favor, completa la verificación de seguridad.")
            else:
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
                        error['captcha'] = _("Verificación de seguridad fallida. Por favor, inténtalo de nuevo.")
                    else:
                        _logger.info("Verificación de Turnstile exitosa")
                    
                except Exception as e:
                    _logger.error(f"Error al verificar Turnstile: {str(e)}")
                    error['captcha'] = _("Error al verificar la seguridad. Por favor, inténtalo de nuevo.")
            
            # Si hay errores, mostrarlos y no continuar con el registro
            if error:
                qcontext.update({'error': error})
                response = request.render('auth_signup.signup', qcontext)
                return self._add_csp_headers(response)
        
        # Continuar con el flujo original de registro si no hay errores
        response = super(TurnstileAuthSignup, self).web_auth_signup(*args, **kw)
        return self._add_csp_headers(response)
        
    @http.route()
    def web_login(self, *args, **kw):
        """
        Mantiene el login original sin cambios (no requiere captcha)
        """
        response = super().web_login(*args, **kw)
        return self._add_csp_headers(response)
    
    @http.route()
    def web_reset_password(self, *args, **kw):
        """
        Mantiene el reset de contraseña original sin cambios
        """
        response = super().web_reset_password(*args, **kw)
        return self._add_csp_headers(response)

    # Método para validar Turnstile mediante una ruta API
    @http.route('/auth_signup/verify_turnstile', type='json', auth='public', website=True, csrf=False)
    def verify_turnstile(self, token=None):
        """
        Endpoint para verificar el token de Turnstile mediante AJAX
        """
        if not token:
            return {'success': False, 'error': 'Token no proporcionado'}
        
        # Obtener la clave secreta de los parámetros del sistema    
        ICP = request.env['ir.config_parameter'].sudo()
        turnstile_secret = ICP.get_param('website.turnstile_secret_key', 
                                         default="0x4AAAAAAA-your_secret_key")
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