# -*- coding: utf-8 -*-
#controllers\captcha_controller.py
from odoo import http, _, fields
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from .email_validator import EmailValidator
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
    1. Restricción por IP: máximo tres usuarios por día
    2. Validación de dominios de correo confiables
    3. Verificación por código enviado al correo
    4. Limitar envío de códigos de verificación a uno por IP por día
    5. Bloqueo de correos que solicitan códigos desde diferentes IPs
    """
    def get_client_ip(self):
        """
        Obtiene la dirección IP real del cliente, incluso detrás de proxies o en entornos Docker
        
        Returns:
            str: La dirección IP del cliente
        """
        request_obj = request.httprequest
        
        # Lista de cabeceras a verificar en orden de prioridad
        ip_headers = [
            'X-Forwarded-For',
            'X-Real-IP',
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_CLIENT_IP',
            'REMOTE_ADDR'
        ]
        
        client_ip = None
        
        # Verificar cabeceras en orden
        for header in ip_headers:
            if header in request_obj.headers:
                ips = request_obj.headers.get(header, '').split(',')
                if ips:
                    client_ip = ips[0].strip()
                    break
                    
        # Si no se encontró en cabeceras, usar remote_addr
        if not client_ip:
            client_ip = request_obj.remote_addr
        
        _logger.debug(f"IP detectada: {client_ip}, cabeceras: {request_obj.headers}")
        return client_ip
    
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
        _logger.info(f"Acceso a formulario de registro desde IP: {self.get_client_ip()}, método: {request.httprequest.method}")

        
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
                _logger.info(f"Iniciando proceso de registro para correo: {email} desde IP: {self.get_client_ip()}")
                
                try:
                    # Validar que el correo no esté bloqueado
                    _logger.debug(f"Validando si el correo {email} está bloqueado")
                    self._validate_email_not_blocked(email)
                    _logger.info(f"Correo {email} no está bloqueado")
                    
                    # Validar límite de IP para registros completos
                    _logger.debug(f"Validando límite de IP para: {self.get_client_ip()}")
                    self._validate_ip_limit()
                    _logger.info(f"Validación de IP exitosa para: {self.get_client_ip()}")
                    
                    # Validar límite de envío de códigos por IP
                    _logger.debug(f"Validando límite de envío de códigos para IP: {self.get_client_ip()}")
                    self._validate_verification_code_limit()
                    _logger.info(f"Validación de límite de envío de códigos exitosa para IP: {self.get_client_ip()}")
                    
                    # Validar que el correo no haya solicitado códigos desde múltiples IPs
                    _logger.debug(f"Validando solicitudes desde múltiples IPs para: {email}")
                    self._validate_multiple_ip_requests(email)
                    _logger.info(f"Validación de múltiples IPs exitosa para: {email}")
                    
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
                    
                    # Registrar el envío de código en la tabla de registros de IP
                    self._register_code_sent(email)
                    
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
                        
                        # Registrar intento fallido
                        self._register_failed_verification_attempt(verification_email)
                        
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
                verification_email = request.session.get('verification_email', '').strip()
                _logger.info(f"Procesando registro final para: {verification_email}")

                if not verification_email:
                    _logger.error("No se pudo obtener el email del usuario para el registro.")
                    qcontext['error'] = _("No se pudo obtener el correo electrónico para el registro. Intente de nuevo.")
                    return request.render('advanced_partner_securit.signup_final', qcontext)

                # Asegurar que los datos necesarios estén en qcontext y kw
                qcontext['login'] = verification_email
                qcontext['email'] = verification_email
                qcontext['name'] = kw.get('name')
                qcontext['password'] = kw.get('password')
                
                # También asegurar que estén en kw
                kw['login'] = verification_email
                kw['email'] = verification_email
                
                try:
                    _logger.debug(f"Registrando usuario con email: {verification_email}")

                    # Registrar IP para el registro completo
                    self._register_ip_usage()

                    # Limpiar datos de sesión después del registro exitoso
                    request.session.pop('verification_code', None)
                    request.session.pop('verification_email', None)
                    request.session.pop('verification_expiry', None)
                    request.session.pop('registration_state', None)

                    _logger.info(f"Procediendo con registro final para: {verification_email}")

                    # Implementación para evitar el uso de get_request()
                    try:
                        # Crear el usuario con do_signup
                        self.do_signup(qcontext)
                        
                        # Hacer commit de la transacción actual
                        request.env.cr.commit()
                        
                        # Intentar autenticar automáticamente (versión corregida)
                        try:
                            uid = request.session.authenticate(verification_email, kw.get('password'))
                            if uid:
                                return request.redirect('/web')
                        except Exception as e:
                            _logger.warning(f"No se pudo autenticar automáticamente: {e}")
                        
                        # Si la autenticación automática falla, redirigir al login
                        return request.redirect('/web/login?message=Su cuenta ha sido creada correctamente. Por favor, inicie sesión.')
                        
                    except Exception as e:
                        _logger.error(f"Error en do_signup: {str(e)}", exc_info=True)
                        qcontext['error'] = str(e)
                        return request.render('advanced_partner_securit.signup_final', qcontext)

                except Exception as e:
                    _logger.error(f"Error en registro final para {verification_email}: {str(e)}", exc_info=True)
                    qcontext['error'] = _("Ha ocurrido un error en el proceso de registro. Por favor, inténtelo de nuevo más tarde.")
                    return request.render('advanced_partner_securit.signup_final', qcontext)

        # Para peticiones GET o estados no reconocidos, mostrar formulario inicial
        _logger.info(f"Mostrando formulario inicial de registro para IP: {self.get_client_ip()}")
        request.session['registration_state'] = 'pre'
        return request.render('auth_signup.signup', qcontext)
    
    def _validate_ip_limit(self):
        """Valida que una IP no haya creado más de tres usuarios por día"""
        ip = self.get_client_ip()
        today = fields.Date.today()
        yesterday = today - timedelta(days=1)

        _logger.debug(f"Validando límite de IP para: {ip}, periodo: {yesterday} - {today}")

        # Buscar registros de IP en las últimas 24 horas con estado 'registered'
        IpRegistration = request.env['auth_signup_security.ip_registration'].sudo()
        registrations = IpRegistration.search([
            ('ip_address', '=', ip),
            ('create_date', '>=', yesterday),
            ('state', '=', 'registered')  # Solo contar registros completos
        ])

        _logger.info(f"Validando límite IP para {ip}, registros existentes: {len(registrations)}")

        if len(registrations) >= 3:  # Permitir hasta 3 registros
            reg_emails = ', '.join([r.email for r in registrations])
            _logger.warning(f"Intento de registro múltiple bloqueado para IP: {ip}, registros previos: {len(registrations)}, correos: {reg_emails}")
            raise UserError(_("Por razones de seguridad, solo se permiten tres registros por día desde la misma dirección IP. Por favor, inténtelo más tarde o contacte al soporte."))

    def _validate_verification_code_limit(self):
        """Valida que una IP no solicite más de un código de verificación por día"""
        ip = self.get_client_ip()
        today = fields.Date.today()
        yesterday = today - timedelta(days=1)

        _logger.debug(f"Validando límite de envío de códigos para IP: {ip}, periodo: {yesterday} - {today}")

        # Buscar registros de códigos enviados en las últimas 24 horas
        IpRegistration = request.env['auth_signup_security.ip_registration'].sudo()
        code_requests = IpRegistration.search([
            ('ip_address', '=', ip),
            ('create_date', '>=', yesterday),
            ('state', '=', 'code_sent')  # Solo contar solicitudes de código
        ])

        _logger.info(f"Validando límite de envío de códigos para IP {ip}, solicitudes existentes: {len(code_requests)}")

        if len(code_requests) >= 1:  # Permitir solo 1 código por IP por día
            req_emails = ', '.join([r.email for r in code_requests])
            _logger.warning(f"Intento de solicitud múltiple de códigos bloqueado para IP: {ip}, solicitudes previas: {len(code_requests)}, correos: {req_emails}")
            raise UserError(_("Por razones de seguridad, solo se permite solicitar un código de verificación por día desde la misma dirección IP. Por favor, inténtelo más tarde o contacte al soporte."))
    
    def _validate_multiple_ip_requests(self, email):
        """
        Valida que un correo no esté solicitando códigos desde diferentes IPs.
        Si se detecta que el correo ha solicitado códigos desde otra IP diferente a la actual,
        se bloquea automáticamente.
        """
        if not email:
            return
            
        current_ip = self.get_client_ip()
        today = fields.Date.today()
        three_days_ago = today - timedelta(days=3)  # Verificar en los últimos 3 días
        
        _logger.debug(f"Validando solicitudes desde múltiples IPs para correo: {email}")
        
        # Buscar todas las solicitudes de código para este correo en los últimos 3 días
        IpRegistration = request.env['auth_signup_security.ip_registration'].sudo()
        email_requests = IpRegistration.search([
            ('email', '=', email),
            ('create_date', '>=', three_days_ago),
            ('state', '=', 'code_sent')
        ])
        
        # Si este correo ya ha solicitado códigos, verificar las IPs
        if email_requests:
            ips_used = set([r.ip_address for r in email_requests])
            
            _logger.info(f"Correo {email} ha solicitado códigos desde las siguientes IPs: {', '.join(ips_used)}")
            
            # Si ya existe una solicitud desde una IP diferente a la actual
            if ips_used and current_ip not in ips_used:
                _logger.warning(f"Correo {email} está solicitando código desde una nueva IP: {current_ip}, IPs anteriores: {', '.join(ips_used)}")
                self._block_email(email, "Solicitud de códigos desde múltiples IPs")
                raise UserError(_("Por razones de seguridad, este correo ha sido bloqueado por solicitar códigos desde diferentes direcciones IP. Por favor, utilice otro correo o contacte al soporte."))
    
    def _validate_email_not_blocked(self, email):
        """Valida que el correo no esté en la lista de correos bloqueados"""
        if not email:
            return
            
        _logger.debug(f"Verificando si el correo {email} está bloqueado")
        BlockedEmail = request.env['auth_signup_security.blocked_email'].sudo()
        blocked = BlockedEmail.search([('email', '=', email)], limit=1)
        
        if blocked:
            _logger.warning(f"Correo bloqueado: {email}, fecha de bloqueo: {blocked.blocked_date}, motivo: {blocked.reason}")
            raise UserError(_("Este correo electrónico ha sido bloqueado por motivos de seguridad. Por favor, utilice otro correo o contacte al soporte."))
    
    def _register_failed_verification_attempt(self, email):
        """Registra un intento fallido de verificación y bloquea el correo si hay demasiados intentos"""
        if not email:
            return
            
        _logger.debug(f"Registrando intento fallido de verificación para correo: {email}")
        
        # Obtener intentos fallidos previos desde la sesión
        failed_attempts = request.session.get('failed_verification_attempts', 0) + 1
        request.session['failed_verification_attempts'] = failed_attempts
        
        max_attempts = 5  # Máximo 5 intentos fallidos
        
        _logger.info(f"Correo {email} ha fallado {failed_attempts} intentos de verificación")
        
        if failed_attempts >= max_attempts:
            # Bloquear el correo
            _logger.warning(f"Correo {email} bloqueado por demasiados intentos fallidos de verificación: {failed_attempts}")
            self._block_email(email, "Exceso de intentos fallidos de verificación")
            
            # Limpiar la sesión
            request.session.pop('verification_code', None)
            request.session.pop('verification_email', None)
            request.session.pop('verification_expiry', None)
            request.session.pop('registration_state', None)
            request.session.pop('failed_verification_attempts', None)
            
            raise UserError(_("Por razones de seguridad, este correo ha sido bloqueado por demasiados intentos fallidos de verificación. Por favor, utilice otro correo o contacte al soporte."))
    
    def _block_email(self, email, reason="Motivos de seguridad"):
        """Bloquea un correo electrónico"""
        if not email:
            return
            
        _logger.debug(f"Bloqueando correo: {email}, motivo: {reason}")
        
        try:
            # Registrar el correo en la tabla de correos bloqueados
            BlockedEmail = request.env['auth_signup_security.blocked_email'].sudo()
            
            # Verificar si ya existe
            existing = BlockedEmail.search([('email', '=', email)], limit=1)
            if existing:
                _logger.info(f"El correo {email} ya estaba bloqueado")
                return existing
            
            # Crear nuevo registro
            blocked = BlockedEmail.create({
                'email': email,
                'reason': reason,
                'is_permanent': False  # Por defecto, bloqueo temporal
            })
            
            _logger.info(f"Correo {email} bloqueado exitosamente, ID: {blocked.id}")
            return blocked
        except Exception as e:
            _logger.error(f"Error al bloquear correo {email}: {str(e)}", exc_info=True)
            # No lanzar excepción para que el flujo principal continúe
    
    def _validate_email_domain(self, email):
        """Valida que el dominio de correo sea confiable y realiza validación adicional"""
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
        
        # AGREGAR ESTA LÍNEA - Realizar validación avanzada del correo
        self._validate_email_advanced(email)
        
        _logger.info(f"Dominio válido: {domain}")
    def _validate_email_advanced(self, email):
        """
        Realiza validación avanzada del correo para detectar patrones sospechosos
        """
        if not email:
            raise UserError(_("Por favor, proporcione una dirección de correo electrónico."))
            
        _logger.debug(f"Iniciando validación avanzada para correo: {email}")
        
        # Importar la clase EmailValidator (asegúrate de importarla correctamente)
        from .email_validator import EmailValidator
        
        # Obtener nivel de validación desde parámetros (por defecto: 2-intermedio)
        ICP = request.env['ir.config_parameter'].sudo()
        validation_level = int(ICP.get_param('auth_signup_security.email_validation_level', '2'))
        
        _logger.debug(f"Aplicando nivel de validación {validation_level} para correo: {email}")
        
        # Nivel 1: Solo validación básica de sintaxis
        if validation_level >= 1:
            if not EmailValidator.validate_email_syntax(email):
                _logger.warning(f"Correo rechazado por sintaxis inválida: {email}")
                raise UserError(_("El formato del correo electrónico no es válido. Por favor, verifique e intente nuevamente."))
        
        # Nivel 2: Incluye detección de patrones sospechosos
        if validation_level >= 2:
            if EmailValidator.is_suspicious_pattern(email):
                _logger.warning(f"Correo rechazado por patrón sospechoso: {email}")
                raise UserError(_("El correo electrónico tiene un patrón sospechoso y ha sido rechazado por motivos de seguridad."))
        
        _logger.info(f"Validación avanzada exitosa para correo: {email}")
        return True
    
    def _generate_verification_code(self):
        """Genera un código de verificación aleatorio de 6 dígitos"""
        code = ''.join(random.choices(string.digits, k=6))
        _logger.debug(f"Generado código de verificación: {code}")
        return code
    
    def _send_verification_email(self, email, code):
        """Envía correo con código de verificación"""
        _logger.debug(f"Preparando envío de correo con código {code} a {email}")

        try:
            # Obtener la plantilla de correo
            template = request.env.ref('advanced_partner_securit.mail_template_user_signup_verification').sudo()
            if not template:
                _logger.error("No se encontró la plantilla de correo para verificación de registro")
                raise UserError(_("No se pudo encontrar la plantilla de correo. Contacte al soporte."))

            _logger.debug(f"Usando plantilla de correo ID: {template.id}")

            # Generar el correo asegurándonos de que 'email_to' es el destinatario correcto
            email_values = {
                'email_to': email,
                'email_cc': False,  # No enviar copias
                'auto_delete': True,  # Eliminar el mensaje después de enviarlo
            }

            mail_id = template.with_context(
                verification_code=code,
                expiry_hours=0.5  # 30 minutos
            ).send_mail(request.env.user.id, email_values=email_values, force_send=True)

            _logger.info(f"Correo enviado a {email}, código: {code}, ID del correo: {mail_id}")

        except Exception as e:
            _logger.error(f"Error al enviar correo a {email}: {str(e)}", exc_info=True)
            raise UserError(_("No se pudo enviar el correo de verificación. Por favor, inténtelo de nuevo más tarde."))

    def _register_code_sent(self, email):
        """Registra el envío de un código de verificación"""
        ip = self.get_client_ip()
        
        _logger.debug(f"Registrando envío de código para IP: {ip}, correo: {email}")
        
        try:
            IpRegistration = request.env['auth_signup_security.ip_registration'].sudo()
            new_record = IpRegistration.create({
                'ip_address': ip,
                'email': email,
                'state': 'code_sent'  # Estado para indicar que se envió un código
            })
            
            _logger.info(f"Registro exitoso de envío de código para {email} desde IP {ip}, registro ID: {new_record.id}")
            return new_record
        except Exception as e:
            _logger.error(f"Error al registrar envío de código para IP {ip}, correo {email}: {str(e)}", exc_info=True)
            raise

    def _register_ip_usage(self):
        """Registra el uso de una IP para crear cuenta"""
        ip = self.get_client_ip()
        email = request.session.get('verification_email', 'unknown')

        _logger.debug(f"Registrando uso de IP: {ip} para correo: {email}")

        try:
            IpRegistration = request.env['auth_signup_security.ip_registration'].sudo()
            new_record = IpRegistration.create({
                'ip_address': ip,
                'email': email,
                'state': 'registered'  # Estado para indicar registro completo
            })

            _logger.info(f"Registro exitoso: nuevo usuario {email} desde IP {ip}, registro ID: {new_record.id}")
            return new_record
        except Exception as e:
            _logger.error(f"Error al registrar uso de IP {ip} para {email}: {str(e)}", exc_info=True)
            raise