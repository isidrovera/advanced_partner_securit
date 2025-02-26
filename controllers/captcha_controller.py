# -*- coding: utf-8 -*-
from odoo import http, _, fields
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.http import request
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import random
import string
import logging

_logger = logging.getLogger(__name__)

class SecurityAuthSignup(AuthSignupHome):
    """
    Sobrescribe el controlador de registro original para añadir controles de seguridad avanzados:
    1. Restricción por IP: máximo un usuario por día
    2. Validación de dominios de correo confiables
    3. Verificación por código enviado al correo
    """
    
    def get_auth_signup_qcontext(self):
        """Sobrescribe para asegurar que providers esté definido y agregar datos de seguridad"""
        qcontext = super(SecurityAuthSignup, self).get_auth_signup_qcontext()
        
        # Asegurarse de que providers esté definido
        if 'providers' not in qcontext or qcontext['providers'] is None:
            qcontext['providers'] = []
            
        # Agregar la verificación al contexto si existe
        verification_code = request.session.get('verification_code')
        verification_email = request.session.get('verification_email')
        verification_expiry = request.session.get('verification_expiry')
        
        if verification_code and verification_email and verification_expiry:
            now = fields.Datetime.now()
            if now <= verification_expiry:
                qcontext['verification_email'] = verification_email
                qcontext['verification_sent'] = True
            else:
                # Limpiar códigos expirados
                request.session.pop('verification_code', None)
                request.session.pop('verification_email', None)
                request.session.pop('verification_expiry', None)
        
        return qcontext
    
    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        """Sobrescribe el método de registro para añadir controles de seguridad"""
        qcontext = self.get_auth_signup_qcontext()
        
        # Estado del registro: 
        # 'pre' - Inicio del registro, muestra formulario inicial
        # 'verify' - Enviado código, muestra formulario de verificación
        # 'submit' - Verificado, procede al registro final
        registration_state = request.session.get('registration_state', 'pre')
        
        # Si estamos en un POST, procesamos según el estado
        if request.httprequest.method == 'POST':
            # 1. Primer paso: validación inicial y envío de código
            if registration_state == 'pre' and kw.get('email'):
                try:
                    # Validar límite de IP
                    self._validate_ip_limit()
                    
                    # Validar dominio de correo
                    email = kw.get('email', '').strip().lower()
                    self._validate_email_domain(email)
                    
                    # Si pasa validaciones, enviar código de verificación
                    verification_code = self._generate_verification_code()
                    verification_expiry = fields.Datetime.now() + timedelta(minutes=30)
                    
                    # Guardar en sesión
                    request.session['verification_code'] = verification_code
                    request.session['verification_email'] = email
                    request.session['verification_expiry'] = verification_expiry
                    request.session['registration_state'] = 'verify'
                    
                    # Enviar correo
                    self._send_verification_email(email, verification_code)
                    
                    # Actualizar contexto
                    qcontext['verification_email'] = email
                    qcontext['verification_sent'] = True
                    qcontext['error'] = None
                    
                    # Renderizar página de verificación
                    return request.render('auth_signup_security.signup_verification', qcontext)
                    
                except UserError as e:
                    qcontext['error'] = str(e)
                
            # 2. Segundo paso: validación del código
            elif registration_state == 'verify' and kw.get('verification_code'):
                stored_code = request.session.get('verification_code')
                verification_expiry = request.session.get('verification_expiry')
                verification_email = request.session.get('verification_email')
                user_code = kw.get('verification_code', '').strip()
                
                now = fields.Datetime.now()
                
                if not stored_code or not verification_expiry or now > verification_expiry:
                    qcontext['error'] = _("El código de verificación ha expirado. Por favor, solicite uno nuevo.")
                    request.session['registration_state'] = 'pre'
                    return request.render('auth_signup.signup', qcontext)
                
                if user_code != stored_code:
                    qcontext['error'] = _("Código de verificación incorrecto. Por favor, inténtelo de nuevo.")
                    return request.render('auth_signup_security.signup_verification', qcontext)
                
                # Código correcto, proceder al registro final
                request.session['registration_state'] = 'submit'
                qcontext['verified'] = True
                
                # Preparar datos para el formulario final
                qcontext['email'] = verification_email
                
                # Renderizar formulario final
                return request.render('auth_signup_security.signup_final', qcontext)
                
            # 3. Tercer paso: registro final
            elif registration_state == 'submit':
                # Validar términos
                if not kw.get('accept_terms'):
                    qcontext['error'] = _("Debes aceptar los términos y condiciones para registrarte.")
                    return request.render('auth_signup_security.signup_final', qcontext)
                
                # Añadir email verificado a los parámetros
                kw['login'] = request.session.get('verification_email')
                
                # Registrar IP
                self._register_ip_usage()
                
                # Limpiar datos de sesión
                request.session.pop('verification_code', None)
                request.session.pop('verification_email', None) 
                request.session.pop('verification_expiry', None)
                request.session.pop('registration_state', None)
                
                # Proceder con el registro estándar
                return super(SecurityAuthSignup, self).web_auth_signup(*args, **kw)
        
        # Para peticiones GET o estados no reconocidos, mostrar formulario inicial
        request.session['registration_state'] = 'pre'
        return request.render('auth_signup.signup', qcontext)
    
    def _validate_ip_limit(self):
        """Valida que una IP no haya creado más de un usuario por día"""
        ip = request.httprequest.remote_addr
        today = fields.Date.today()
        yesterday = today - timedelta(days=1)
        
        # Buscar registros de IP en las últimas 24 horas
        IpRegistration = request.env['auth_signup_security.ip_registration'].sudo()
        registrations = IpRegistration.search([
            ('ip_address', '=', ip),
            ('create_date', '>=', yesterday)
        ])
        
        if registrations:
            raise UserError(_("Por razones de seguridad, solo se permite un registro por día desde la misma dirección IP. Por favor, inténtelo más tarde o contacte al soporte."))
    
    def _validate_email_domain(self, email):
        """Valida que el dominio de correo sea confiable"""
        if not email or '@' not in email:
            raise UserError(_("Por favor, proporcione una dirección de correo electrónico válida."))
        
        domain = email.split('@')[1].lower()
        
        # Obtener dominios permitidos de la configuración
        ICP = request.env['ir.config_parameter'].sudo()
        allowed_domains_str = ICP.get_param('auth_signup_security.allowed_email_domains', 
                                           'gmail.com,hotmail.com,outlook.com,yahoo.com,live.com,icloud.com')
        allowed_domains = [d.strip().lower() for d in allowed_domains_str.split(',')]
        
        if domain not in allowed_domains:
            raise UserError(_("Por razones de seguridad, solo se aceptan correos de dominios confiables. Los dominios permitidos son: %s") % allowed_domains_str)
    
    def _generate_verification_code(self):
        """Genera un código de verificación aleatorio de 6 dígitos"""
        return ''.join(random.choices(string.digits, k=6))
    
    def _send_verification_email(self, email, code):
        """Envía correo con código de verificación"""
        template = request.env.ref('auth_signup_security.mail_template_user_signup_verification')
        if template:
            template_values = {
                'email_to': email,
                'verification_code': code,
                'expiry_hours': 0.5,  # 30 minutos
            }
            template.with_context(**template_values).send_mail(request.env.user.id, force_send=True)
        _logger.info(f"Código de verificación enviado a {email}: {code}")
    
    def _register_ip_usage(self):
        """Registra el uso de una IP para crear cuenta"""
        ip = request.httprequest.remote_addr
        IpRegistration = request.env['auth_signup_security.ip_registration'].sudo()
        IpRegistration.create({
            'ip_address': ip,
            'email': request.session.get('verification_email', 'unknown')
        })