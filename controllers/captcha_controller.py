# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
import requests
import logging
import werkzeug
import json
from odoo import http
from odoo.http import Response, request

_logger = logging.getLogger(__name__)

class TurnstileAuthSignup(AuthSignupHome):
    
    @http.route()
    def web_auth_signup(self, *args, **kw):
        """Sobrescribe el método de registro para validar Turnstile"""
        _logger.info("Procesando registro con validación Turnstile")
        
        # Obtener la clave secreta de los parámetros del sistema
        ICP = request.env['ir.config_parameter'].sudo()
        turnstile_secret = ICP.get_param('website.turnstile_secret_key', 
                                        default="0x4AAAAAAA-your_secret_key")
        turnstile_verify_url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
        
        # Obtener el token de la respuesta del captcha
        turnstile_response = kw.get('cf-turnstile-response')
        
        # Verificar si se está enviando un formulario (POST)
        if request.httprequest.method == 'POST':
            # Inicializar el diccionario de errores de forma adecuada para que funcione con el XML
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
                return request.render('auth_signup.signup', qcontext)
        
        # Continuar con el flujo original de registro si no hay errores
        return super().web_auth_signup(*args, **kw)

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup_override(self, *args, **kw):
        """
        Sobrescribe la ruta de registro para asegurar que el captcha se valide
        """
        # Agregar encabezados CSP directamente en la respuesta
        response = self.web_auth_signup(*args, **kw)
        
        # Si la respuesta es un objeto Response, agregar los encabezados
        if hasattr(response, 'headers'):
            csp = "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://challenges.cloudflare.com; " + \
                  "frame-src 'self' https://challenges.cloudflare.com; " + \
                  "connect-src 'self' https://challenges.cloudflare.com;"
                  
            response.headers['Content-Security-Policy'] = csp
        
        return response
        
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
            
            

class CSPController(http.Controller):
    """
    Controlador para modificar las políticas de seguridad de contenido (CSP) en rutas específicas
    """
    
    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def signup_with_csp(self, *args, **kw):
        """
        Intercepta la solicitud de registro para inyectar los encabezados CSP necesarios
        """
        _logger.info("Interceptando ruta de registro para ajustar CSP")
        
        # Permitir que el controlador original maneje la solicitud
        # Delegamos al controlador original sin usar super() ya que estamos interceptando
        response = request.env['ir.http']._dispatch()
        
        # Modificar los encabezados CSP en la respuesta
        if isinstance(response, Response) and hasattr(response, 'headers'):
            csp_policy = (
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://challenges.cloudflare.com; "
                "frame-src 'self' https://challenges.cloudflare.com; "
                "connect-src 'self' https://challenges.cloudflare.com;"
            )
            
            # Establecer o actualizar la política CSP
            response.headers['Content-Security-Policy'] = csp_policy
            _logger.info("CSP modificado para la página de registro")
            
        return response