# -*- coding: utf-8 -*-
#controllers\email_validator.py
import re
import logging

_logger = logging.getLogger(__name__)

class EmailValidator:
    """
    Clase para validar correos electrónicos y detectar patrones sospechosos.
    """
    
    @staticmethod
    def validate_email_syntax(email):
        """
        Valida la sintaxis del correo electrónico de manera más estricta.
        """
        if not email or '@' not in email:
            return False
            
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            return False
            
        local_part, domain = email.split('@', 1)
        if len(local_part) > 64 or len(domain) > 255:
            return False
            
        if '.' not in domain:
            return False
            
        if '..' in email or '__' in email or '--' in email:
            return False
            
        return True
    
    @staticmethod
    def is_suspicious_pattern(email):
        """
        Detecta patrones sospechosos en correos que suelen indicar bots o spam
        """
        if not email or '@' not in email:
            return True
            
        local_part = email.split('@')[0].lower()
        
        # 1. Secuencias de caracteres repetidos
        repetition_pattern = r'(.)\1{4,}'  # 5 o más caracteres idénticos
        if re.search(repetition_pattern, local_part):
            _logger.info(f"Correo sospechoso: {email} - Contiene caracteres repetidos")
            return True
        
        # 2. Patrones de teclado reconocibles
        keyboard_patterns = ['qwerty', 'asdfgh', '123456', 'zxcvbn', 'qazwsx']
        for pattern in keyboard_patterns:
            if pattern in local_part:
                _logger.info(f"Correo sospechoso: {email} - Contiene patrón de teclado: {pattern}")
                return True
        
        # 3. Demasiadas consonantes consecutivas
        consonant_pattern = r'[bcdfghjklmnpqrstvwxyz]{5,}'  # 5+ consonantes seguidas
        if re.search(consonant_pattern, local_part):
            _logger.info(f"Correo sospechoso: {email} - Demasiadas consonantes consecutivas")
            return True
        
        # 4. Nombres muy cortos con dominio común
        if len(local_part) < 3:
            _logger.info(f"Correo sospechoso: {email} - Parte local demasiado corta: {local_part}")
            return True
        
        # 5. Todos números en la parte local
        if re.match(r'^[0-9]+$', local_part):
            _logger.info(f"Correo sospechoso: {email} - Parte local solo contiene números")
            return True
            
        return False