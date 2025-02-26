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
        
        _logger.debug("Obteniendo contexto para formulario de registro")
        
        # Asegurarse de que providers esté definido
        if 'providers' not in qcontext or qcontext['providers'] is None:
            qcontext['providers'] = []
            _logger.debug("Providers no definido, inicializando como lista vacía")
            
        # Agregar la verificación al contexto si existe
        verification_code = request.session.get('verification_code')
        verification_email = request.session.get('verification_email')
        verification_expiry_str = request.session.get('verification_expiry')
        
        if verification_code and verification_email and verification_expiry_str:
            now = fields.Datetime.now()
            try:
                # Convertir la cadena ISO a datetime
                verification_expiry = fields.Datetime.from_string(verification_expiry_str)
                _logger.debug(f"Verificando estado de código para {verification_email}, expira: {verification_expiry}, ahora: {now}")
                
                if now <= verification_expiry:
                    qcontext['verification_email'] = verification_email
                    qcontext['verification_sent'] = True
                    _logger.debug(f"Código de verificación válido para {verification_email}")
                else:
                    # Limpiar códigos expirados
                    _logger.info(f"Limpiando código expirado para {verification_email}")
                    request.session.pop('verification_code', None)
                    request.session.pop('verification_email', None)
                    request.session.pop('verification_expiry', None)
            except Exception as e:
                _logger.error(f"Error al procesar fecha de expiración: {str(e)}", exc_info=True)
                # Limpiar datos de sesión inválidos
                request.session.pop('verification_code', None)
                request.session.pop('verification_email', None)
                request.session.pop('verification_expiry', None)
        
        return qcontext
    
    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        """Sobrescribe el método de registro para añadir controles de seguridad"""
        _logger.info(f"Acceso a formulario de registro desde IP: {request.httprequest.remote_addr}, método: {request.httprequest.method}")
        
        qcontext = self.get_auth_signup_qcontext()
        
        # Estado del registro: 
        # 'pre' - Inicio del registro, muestra formulario inicial
        # 'verify' - Enviado código, muestra formulario de verificación
        # 'submit' - Verificado, procede al registro final
        registration_state = request.session.get('registration_state', 'pre')
        _logger.info(f"Estado actual del registro: {registration_state}")
        
        # Si estamos en un POST, procesamos según el estado
        if request.httprequest.method == 'POST':
            _logger.info(f"Procesando petición POST en estado: {registration_state}")
            
            # 1. Primer paso: validación inicial y envío de código
            if registration_state == 'pre' and kw.get('email'):
                email = kw.get('email', '').strip().lower()
                _logger.info(f"Iniciando proceso de registro para correo: {email} desde IP: {request.httprequest.remote_addr}")
                
                try:
                    # Validar límite de IP
                    _logger.debug(f"Validando límite de IP para: {request.httprequest.remote_addr}")
                    self._validate_ip_limit()
                    _logger.info(f"Validación de IP exitosa para: {request.httprequest.remote_addr}")
                    
                    # Validar dominio de correo
                    _logger.debug(f"Validando dominio de correo para: {email}")
                    self._validate_email_domain(email)
                    _logger.info(f"Validación de dominio exitosa para correo: {email}")
                    
                    # Si pasa validaciones, enviar código de verificación
                    verification_code = self._generate_verification_code()
                    verification_expiry = fields.Datetime.now() + timedelta(minutes=30)
                    
                    # Convertir datetime a string ISO para almacenamiento en sesión
                    verification_expiry_str = fields.Datetime.to_string(verification_expiry)
                    
                    _logger.debug(f"Generado código de verificación: {verification_code} para: {email}, expira: {verification_expiry}")
                    
                    # Guardar en sesión
                    request.session['verification_code'] = verification_code
                    request.session['verification_email'] = email
                    request.session['verification_expiry'] = verification_expiry_str  # Guardar como string
                    request.session['registration_state'] = 'verify'
                    
                    # Enviar correo
                    _logger.debug(f"Enviando correo con código a: {email}")
                    self._send_verification_email(email, verification_code)
                    _logger.info(f"Código de verificación enviado a {email}, expira en: {verification_expiry}")
                    
                    # Actualizar contexto
                    qcontext['verification_email'] = email
                    qcontext['verification_sent'] = True
                    qcontext['error'] = None
                    
                    # Renderizar página de verificación
                    _logger.info(f"Redirigiendo a página de verificación para: {email}")
                    return request.render('advanced_partner_securit.signup_verification', qcontext)
                    
                except UserError as e:
                    _logger.warning(f"Error en validación de registro para {email}: {str(e)}")
                    qcontext['error'] = str(e)
                except Exception as e:
                    _logger.error(f"Error inesperado en registro para {email}: {str(e)}", exc_info=True)
                    qcontext['error'] = _("Ha ocurrido un error en el proceso de registro. Por favor, inténtelo de nuevo más tarde.")
                
            # 2. Segundo paso: validación del código
            elif registration_state == 'verify' and kw.get('verification_code'):
                stored_code = request.session.get('verification_code')
                verification_expiry_str = request.session.get('verification_expiry')
                verification_email = request.session.get('verification_email')
                user_code = kw.get('verification_code', '').strip()
                
                _logger.info(f"Verificando código para {verification_email}: código ingresado: {user_code}")
                
                now = fields.Datetime.now()
                
                if not stored_code or not verification_expiry_str:
                    _logger.warning(f"No se encontró código almacenado o fecha de expiración para {verification_email}")
                    qcontext['error'] = _("Ha ocurrido un error con el código de verificación. Por favor, solicite uno nuevo.")
                    request.session['registration_state'] = 'pre'
                    return request.render('auth_signup.signup', qcontext)
                
                try:
                    # Convertir la cadena ISO a datetime
                    verification_expiry = fields.Datetime.from_string(verification_expiry_str)
                    
                    if now > verification_expiry:
                        _logger.warning(f"Código expirado para {verification_email}, expiración: {verification_expiry}, ahora: {now}")
                        qcontext['error'] = _("El código de verificación ha expirado. Por favor, solicite uno nuevo.")
                        request.session['registration_state'] = 'pre'
                        return request.render('auth_signup.signup', qcontext)
                    
                    if user_code != stored_code:
                        _logger.warning(f"Código incorrecto para {verification_email}: esperado {stored_code}, recibido {user_code}")
                        qcontext['error'] = _("Código de verificación incorrecto. Por favor, inténtelo de nuevo.")
                        return request.render('advanced_partner_securit.signup_verification', qcontext)
                    
                    # Código correcto, proceder al registro final
                    _logger.info(f"Código verificado correctamente para {verification_email}")
                    request.session['registration_state'] = 'submit'
                    qcontext['verified'] = True
                    
                    # Preparar datos para el formulario final
                    qcontext['email'] = verification_email
                    
                    # Renderizar formulario final
                    _logger.info(f"Redirigiendo a formulario final para: {verification_email}")
                    return request.render('advanced_partner_securit.signup_final', qcontext)
                except Exception as e:
                    _logger.error(f"Error al procesar verificación: {str(e)}", exc_info=True)
                    qcontext['error'] = _("Ha ocurrido un error al verificar el código. Por favor, inténtelo de nuevo.")
                    return request.render('advanced_partner_securit.signup_verification', qcontext)
                
            # 3. Tercer paso: registro final
            elif registration_state == 'submit':
                verification_email = request.session.get('verification_email')
                _logger.info(f"Procesando registro final para: {verification_email}")
                
                # Validar términos
                if not kw.get('accept_terms'):
                    _logger.warning(f"Términos y condiciones no aceptados para: {verification_email}")
                    qcontext['error'] = _("Debes aceptar los términos y condiciones para registrarte.")
                    return request.render('advanced_partner_securit.signup_final', qcontext)
                
                # Validar que la contraseña y la confirmación coincidan
                if kw.get('password') != kw.get('confirm_password'):
                    _logger.warning(f"Las contraseñas no coinciden para: {verification_email}")
                    qcontext['error'] = _("Las contraseñas no coinciden. Por favor, inténtelo de nuevo.")
                    return request.render('advanced_partner_securit.signup_final', qcontext)
                
                # Añadir email verificado a los parámetros
                kw['login'] = verification_email
                
                try:
                    # Registrar IP
                    _logger.debug(f"Registrando uso de IP para: {request.httprequest.remote_addr}, correo: {verification_email}")
                    self._register_ip_usage()
                    
                    # Limpiar datos de sesión
                    request.session.pop('verification_code', None)
                    request.session.pop('verification_email', None) 
                    request.session.pop('verification_expiry', None)
                    request.session.pop('registration_state', None)
                    
                    _logger.info(f"Procediendo con registro final para: {verification_email}")
                    
                    # Proceder con el registro estándar
                    return super(SecurityAuthSignup, self).web_auth_signup(*args, **kw)
                except Exception as e:
                    _logger.error(f"Error en registro final para {verification_email}: {str(e)}", exc_info=True)
                    qcontext['error'] = _("Ha ocurrido un error en el proceso de registro. Por favor, inténtelo de nuevo más tarde.")
                    return request.render('advanced_partner_securit.signup_final', qcontext)
        
        # Para peticiones GET o estados no reconocidos, mostrar formulario inicial
        _logger.info(f"Mostrando formulario inicial de registro para IP: {request.httprequest.remote_addr}")
        request.session['registration_state'] = 'pre'
        return request.render('auth_signup.signup', qcontext)
    
    def _validate_ip_limit(self):
        """Valida que una IP no haya creado más de un usuario por día"""
        ip = request.httprequest.remote_addr
        today = fields.Date.today()
        yesterday = today - timedelta(days=1)
        
        _logger.debug(f"Validando límite de IP para: {ip}, periodo: {yesterday} - {today}")
        
        # Buscar registros de IP en las últimas 24 horas
        IpRegistration = request.env['auth_signup_security.ip_registration'].sudo()
        registrations = IpRegistration.search([
            ('ip_address', '=', ip),
            ('create_date', '>=', yesterday)
        ])
        
        _logger.info(f"Validando límite IP para {ip}, registros existentes: {len(registrations)}")
        
        if registrations:
            reg_emails = ', '.join([r.email for r in registrations])
            _logger.warning(f"Intento de registro múltiple bloqueado para IP: {ip}, registros previos: {len(registrations)}, correos: {reg_emails}")
            raise UserError(_("Por razones de seguridad, solo se permite un registro por día desde la misma dirección IP. Por favor, inténtelo más tarde o contacte al soporte."))
    
    def _validate_email_domain(self, email):
        """Valida que el dominio de correo sea confiable"""
        if not email or '@' not in email:
            _logger.warning(f"Formato de correo inválido: {email}")
            raise UserError(_("Por favor, proporcione una dirección de correo electrónico válida."))
        
        domain = email.split('@')[1].lower()
        _logger.debug(f"Validando dominio de correo: {domain}")
        
        # Obtener dominios permitidos de la configuración
        ICP = request.env['ir.config_parameter'].sudo()
        allowed_domains_str = ICP.get_param('auth_signup_security.allowed_email_domains', 
                                           'gmail.com,hotmail.com,outlook.com,yahoo.com,live.com,icloud.com')
        allowed_domains = [d.strip().lower() for d in allowed_domains_str.split(',')]
        
        _logger.debug(f"Dominios permitidos: {allowed_domains}")
        
        if domain not in allowed_domains:
            _logger.warning(f"Dominio no permitido: {domain}, dominios permitidos: {allowed_domains_str}")
            raise UserError(_("Por razones de seguridad, solo se aceptan correos de dominios confiables. Los dominios permitidos son: %s") % allowed_domains_str)
        
        _logger.info(f"Dominio válido: {domain}")
    
    def _generate_verification_code(self):
        """Genera un código de verificación aleatorio de 6 dígitos"""
        code = ''.join(random.choices(string.digits, k=6))
        _logger.debug(f"Generado código de verificación: {code}")
        return code
    
    def _send_verification_email(self, email, code):
        """Envía correo con código de verificación"""
        _logger.debug(f"Preparando envío de correo con código {code} a {email}")
        
        try:
            # Usar sudo() para acceder y enviar el correo con permisos de administrador
            template = request.env.ref('advanced_partner_securit.mail_template_user_signup_verification').sudo()
            if template:
                mail_values = {
                    'email_to': email,
                    'body_html': template.body_html.replace("{{ ctx['verification_code'] }}", code)
                                                .replace("{{ ctx['expiry_hours'] }}", str(0.5)),
                    'subject': template.subject,
                }
                
                _logger.debug(f"Enviando correo con código {code} a {email}")

                mail_id = template.send_mail(
                    request.env.user.id, email_values=mail_values, force_send=True
                )
                
                _logger.info(f"Correo enviado a {email}, código: {code}, ID del correo: {mail_id}")

                        else:
                _logger.error(f"No se encontró la plantilla de correo para verificación de registro")
        except Exception as e:
            _logger.error(f"Error al enviar correo a {email}: {str(e)}", exc_info=True)
            raise UserError(_("No se pudo enviar el correo de verificación. Por favor, inténtelo de nuevo más tarde."))
    def _register_ip_usage(self):
        """Registra el uso de una IP para crear cuenta"""
        ip = request.httprequest.remote_addr
        email = request.session.get('verification_email', 'unknown')
        
        _logger.debug(f"Registrando uso de IP: {ip} para correo: {email}")
        
        try:
            IpRegistration = request.env['auth_signup_security.ip_registration'].sudo()
            new_record = IpRegistration.create({
                'ip_address': ip,
                'email': email
            })
            
            _logger.info(f"Registro exitoso: nuevo usuario {email} desde IP {ip}, registro ID: {new_record.id}")
            return new_record
        except Exception as e:
            _logger.error(f"Error al registrar uso de IP {ip} para {email}: {str(e)}", exc_info=True)
            raise