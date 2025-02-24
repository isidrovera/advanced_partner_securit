# -*- coding: utf-8 -*-

import logging
import werkzeug
import requests
import random
import string
from datetime import datetime, timedelta
from odoo import http, _, fields
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.web.controllers.main import ensure_db, Home
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AuthSignupExtended(AuthSignupHome):

    def get_auth_signup_qcontext(self):
        """Extend signup context to add our custom fields and errors"""
        qcontext = super(AuthSignupExtended, self).get_auth_signup_qcontext()
        qcontext.update({
            'recaptcha_site_key': request.env['ir.config_parameter'].sudo().get_param('recaptcha.site_key', ''),
        })
        
        if request.httprequest.method == 'POST':
            if not qcontext.get('error'):
                qcontext['error'] = {}
                
            # Check captcha
            if not self.validate_captcha(request.params.get('g-recaptcha-response')):
                qcontext['error']['captcha'] = _("Por favor, completa el captcha correctamente.")
                
            # Check terms acceptance
            if 'accept_terms' not in request.params:
                qcontext['error']['terms'] = _("Debes aceptar los términos y condiciones.")
                
            # Check IP restriction
            if not self.validate_ip_restriction():
                qcontext['error']['ip'] = _("Has alcanzado el límite de registros desde esta IP.")
                
            # Check email domain
            if 'login' in request.params and not self.validate_email_domain(request.params['login']):
                qcontext['error']['login'] = _("Este dominio de correo electrónico no está permitido.")
                
        return qcontext

    def validate_captcha(self, captcha_response):
        """Validate the reCAPTCHA response"""
        if not captcha_response:
            return False
            
        secret_key = request.env['ir.config_parameter'].sudo().get_param('recaptcha.secret_key', '')
        if not secret_key:
            _logger.warning("reCAPTCHA secret_key no configurada")
            return True  # Skip validation if not configured
            
        try:
            response = requests.post(
                'https://www.google.com/recaptcha/api/siteverify',
                data={
                    'secret': secret_key,
                    'response': captcha_response,
                    'remoteip': request.httprequest.remote_addr
                }
            )
            result = response.json()
            return result.get('success', False)
        except Exception as e:
            _logger.exception("Error validando reCAPTCHA: %s", str(e))
            return False

    def validate_ip_restriction(self):
        """Check if this IP has already registered too many accounts today"""
        ip_address = request.httprequest.remote_addr
        
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59)
        
        count = request.env['res.partner'].sudo().search_count([
            ('registration_ip', '=', ip_address),
            ('registration_date', '>=', today_start),
            ('registration_date', '<=', today_end),
        ])
        
        return count < 3  # Limit to 3 registrations per day per IP

    def validate_email_domain(self, email):
        """Validate that the email domain is allowed"""
        if not email:
            return False
            
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
        """Override signup to add email verification"""
        qcontext = self.get_auth_signup_qcontext()
        
        if 'error' in qcontext and qcontext['error']:
            return request.render('auth_signup.signup', qcontext)
            
        if request.httprequest.method == 'POST':
            # Validar captcha, IP y dominio de correo antes de proceder
            if not qcontext.get('error', {}):
                try:
                    # Crear usuario no verificado
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
                    
                    verification_id = request.env['user.verification'].sudo().create(verification_vals)
                    
                    # Enviar correo con el código de verificación
                    template = request.env.ref('advanced_partner_security.mail_template_verification_code')
                    template.sudo().with_context(
                        name=name,
                        verification_code=verification_code
                    ).send_mail(verification_id.id, force_send=True)
                    
                    # Redirigir a la página de verificación
                    return werkzeug.utils.redirect(f'/verify?token={verification_token}')
                    
                except Exception as e:
                    _logger.exception("Error durante el registro: %s", str(e))
                    qcontext['error'] = _("Ocurrió un error durante el registro. Por favor intente nuevamente.")
                    
        return super(AuthSignupExtended, self).web_auth_signup(*args, **kw)

    @http.route('/verify', type='http', auth='public', website=True)
    def verification_page(self, token=None, **kw):
        """Display verification page"""
        if not token:
            return werkzeug.utils.redirect('/web/login')
            
        error = kw.get('error')
        
        return request.render('advanced_partner_security.email_verification_page', {
            'token': token,
            'error': error
        })

    @http.route('/verify/email', type='http', auth='public', website=True)
    def verify_email(self, token=None, verification_code=None, **kw):
        """Verify email verification code"""
        if not token or not verification_code:
            return werkzeug.utils.redirect('/web/login')
            
        verification = request.env['user.verification'].sudo().search([
            ('verification_token', '=', token),
            ('verification_code', '=', verification_code),
            ('expiration', '>=', fields.Datetime.now()),
            ('used', '=', False)
        ], limit=1)
        
        if not verification:
            return self.verification_page(token=token, error=_("Código de verificación inválido o expirado."))
            
        try:
            # Marcar la verificación como usada
            verification.write({'used': True})
            
            # Crear usuario utilizando los datos almacenados
            values = {
                'login': verification.login,
                'name': verification.name,
                'password': verification.password,
                'registration_ip': verification.ip_address,
                'registration_date': fields.Datetime.now(),
                'is_verified_email': True,
            }
            
            db, login, password = request.env['res.users'].sudo().signup(values, qcontext.get('token'))
            
            # Autenticar al usuario directamente
            request.env.cr.commit()
            return request.env['res.users'].sudo().web_login(verification.login, verification.password)
            
        except Exception as e:
            _logger.exception("Error durante la verificación: %s", str(e))
            return self.verification_page(token=token, error=_("Ocurrió un error durante la verificación."))

    @http.route('/resend/verification', type='http', auth='public', website=True)
    def resend_verification(self, token=None, **kw):
        """Resend verification code"""
        if not token:
            return werkzeug.utils.redirect('/web/login')
            
        verification = request.env['user.verification'].sudo().search([
            ('verification_token', '=', token),
            ('used', '=', False),
        ], limit=1)
        
        if not verification:
            return werkzeug.utils.redirect('/web/login')
            
        # Generar nuevo código y actualizar fecha de expiración
        new_code = ''.join(random.choices(string.digits, k=6))
        verification.write({
            'verification_code': new_code,
            'expiration': fields.Datetime.now() + timedelta(minutes=10)
        })
        
        # Enviar el nuevo código por correo
        template = request.env.ref('advanced_partner_security.mail_template_verification_code')
        template.sudo().with_context(
            name=verification.name,
            verification_code=new_code
        ).send_mail(verification.id, force_send=True)
        
        return self.verification_page(token=token, error=_("Se ha enviado un nuevo código de verificación a tu correo."))