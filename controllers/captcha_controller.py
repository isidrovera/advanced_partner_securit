# -*- coding: utf-8 -*-

import logging
import werkzeug
import requests
import random
import string
from datetime import datetime, timedelta

from odoo import http, _, fields
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.http import request

_logger = logging.getLogger(__name__)

class AuthSignupExtended(AuthSignupHome):
    def get_auth_signup_qcontext(self):
        """Extender el contexto del registro y validar Turnstile"""
        qcontext = super(AuthSignupExtended, self).get_auth_signup_qcontext()

        if request.httprequest.method == 'POST':
            qcontext['error'] = {}

            # Validar Turnstile
            turnstile_response = request.params.get('cf-turnstile-response')
            if not self.validate_turnstile(turnstile_response):
                qcontext['error']['captcha'] = _("Por favor, completa el captcha correctamente.")

        return qcontext

    def validate_turnstile(self, response):
        """Verificar respuesta de Turnstile con Cloudflare"""
        if not response:
            return False
        
        secret_key = request.env['ir.config_parameter'].sudo().get_param('turnstile.secret_key', '')
        if not secret_key:
            _logger.warning("Clave secreta de Turnstile no configurada")
            return True  # Si no está configurada, no se bloquea

        try:
            response = requests.post(
                'https://challenges.cloudflare.com/turnstile/v0/siteverify',
                data={'secret': secret_key, 'response': response, 'remoteip': request.httprequest.remote_addr},
                timeout=5
            )
            result = response.json()
            return result.get('success', False)
        except Exception as e:
            _logger.exception("Error validando Turnstile: %s", str(e))
            return False

    @http.route('/web/signup', type='http', auth='public', website=True)
    def web_auth_signup(self, *args, **kw):
        """Sobrescribir el registro de usuario para validar Turnstile"""
        qcontext = self.get_auth_signup_qcontext()

        if 'error' in qcontext and qcontext['error']:
            return request.render('auth_signup.signup', qcontext)

        return super(AuthSignupExtended, self).web_auth_signup(*args, **kw)

    def validate_ip_restriction(self):
        """Verificar si esta IP ya ha registrado demasiadas cuentas hoy"""
        ip_address = request.httprequest.remote_addr
        
        # Definir el rango de tiempo para hoy
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59)
        
        # Contar registros desde esta IP hoy
        count = request.env['res.partner'].sudo().search_count([
            ('registration_ip', '=', ip_address),
            ('registration_date', '>=', today_start),
            ('registration_date', '<=', today_end),
        ])
        
        # Limitar a 3 registros por día por IP
        return count < 3

    def validate_email_domain(self, email):
        """Validar que el dominio de correo esté permitido"""
        if not email:
            return False
        
        # Obtener el dominio del correo
        domain = email.split('@')[-1].lower()
        
        # Lista de dominios temporales/desechables a bloquear
        disposable_domains = [
            'mailinator.com', 'yopmail.com', 'tempmail.com', 'guerrillamail.com', 
            'temp-mail.org', 'throwawaymail.com', '10minutemail.com', 'mailnesia.com',
            'trash-mail.com', 'getairmail.com', 'mailnull.com', 'spamgourmet.com',
            'sharklasers.com', 'spam4.me', 'dispostable.com', 'nada.email',
            'getnada.com', 'spamex.com', 'mytrashmail.com'
        ]
        
        return domain not in disposable_domains

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        """Sobrescribir registro para agregar verificación de correo"""
        # Obtener el contexto de registro
        qcontext = self.get_auth_signup_qcontext()
        
        # Si hay errores, renderizar el formulario de registro con los errores
        if 'error' in qcontext and qcontext['error']:
            return request.render('auth_signup.signup', qcontext)
        
        # Si es un POST, realizar validaciones
        if request.httprequest.method == 'POST':
            # Si no hay errores previos
            if not qcontext.get('error', {}):
                try:
                    # Obtener datos del formulario
                    login = qcontext.get('login', '')
                    name = qcontext.get('name', '')
                    password = qcontext.get('password', '')
                    
                    # Generar código de verificación y token
                    verification_code = ''.join(random.choices(string.digits, k=6))
                    verification_token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
                    
                    # Almacenar datos de verificación en la base de datos
                    verification_vals = {
                        'login': login,
                        'name': name,
                        'password': password,
                        'verification_code': verification_code,
                        'verification_token': verification_token,
                        'expiration': fields.Datetime.now() + timedelta(minutes=10),
                        'ip_address': request.httprequest.remote_addr,
                    }
                    
                    # Crear registro de verificación
                    verification_id = request.env['user.verification'].sudo().create(verification_vals)
                    
                    # Enviar correo con código de verificación
                    template = request.env.ref('advanced_partner_security.mail_template_verification_code')
                    template.sudo().with_context(
                        name=name,
                        verification_code=verification_code
                    ).send_mail(verification_id.id, force_send=True)
                    
                    # Redirigir a página de verificación
                    return werkzeug.utils.redirect(f'/verify?token={verification_token}')
                
                except Exception as e:
                    _logger.exception("Error durante el registro: %s", str(e))
                    qcontext['error'] = _("Ocurrió un error durante el registro. Por favor intente nuevamente.")
        
        # Si no es un POST o hay errores, usar el método de registro original
        return super(AuthSignupExtended, self).web_auth_signup(*args, **kw)

    @http.route('/verify', type='http', auth='public', website=True)
    def verification_page(self, token=None, **kw):
        """Mostrar página de verificación"""
        if not token:
            return werkzeug.utils.redirect('/web/login')
        
        error = kw.get('error')
        
        return request.render('advanced_partner_security.email_verification_page', {
            'token': token,
            'error': error
        })

    @http.route('/verify/email', type='http', auth='public', website=True)
    def verify_email(self, token=None, verification_code=None, **kw):
        """Verificar código de verificación de correo"""
        if not token or not verification_code:
            return werkzeug.utils.redirect('/web/login')
        
        # Buscar registro de verificación
        verification = request.env['user.verification'].sudo().search([
            ('verification_token', '=', token),
            ('verification_code', '=', verification_code),
            ('expiration', '>=', fields.Datetime.now()),
            ('used', '=', False)
        ], limit=1)
        
        if not verification:
            return self.verification_page(token=token, error=_("Código de verificación inválido o expirado."))
        
        try:
            # Marcar verificación como usada
            verification.write({'used': True})
            
            # Preparar valores para crear usuario
            values = {
                'login': verification.login,
                'name': verification.name,
                'password': verification.password,
                'registration_ip': verification.ip_address,
                'registration_date': fields.Datetime.now(),
                'is_verified_email': True,
            }
            
            # Crear usuario
            user = request.env['res.users'].sudo().with_context(no_reset_password=True).create(values)
            
            # Confirmar transacción
            request.env.cr.commit()
            
            # Intentar iniciar sesión
            return request.env['res.users'].sudo()._login_attempt(user.login, verification.password, {'interactive': True})
        
        except Exception as e:
            _logger.exception("Error durante la verificación: %s", str(e))
            return self.verification_page(token=token, error=_("Ocurrió un error durante la verificación."))

    @http.route('/resend/verification', type='http', auth='public', website=True)
    def resend_verification(self, token=None, **kw):
        """Reenviar código de verificación"""
        if not token:
            return werkzeug.utils.redirect('/web/login')
        
        # Buscar registro de verificación
        verification = request.env['user.verification'].sudo().search([
            ('verification_token', '=', token),
            ('used', '=', False),
        ], limit=1)
        
        if not verification:
            return werkzeug.utils.redirect('/web/login')
        
        # Generar nuevo código
        new_code = ''.join(random.choices(string.digits, k=6))
        verification.write({
            'verification_code': new_code,
            'expiration': fields.Datetime.now() + timedelta(minutes=10)
        })
        
        # Enviar nuevo código por correo
        template = request.env.ref('advanced_partner_security.mail_template_verification_code')
        template.sudo().with_context(
            name=verification.name,
            verification_code=new_code
        ).send_mail(verification.id, force_send=True)
        
        return self.verification_page(token=token, error=_("Se ha enviado un nuevo código de verificación a tu correo."))