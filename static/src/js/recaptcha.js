/** @odoo-module **/

import { registry } from "@web/core/registry";
import { onMounted } from "@odoo/owl";

const recaptchaValidator = {
    /**
     * Validar la respuesta de reCAPTCHA antes de enviar el formulario
     * @param {Event} ev - Evento de envío del formulario
     */
    validateRecaptcha: function (ev) {
        // Obtener el elemento del formulario
        const form = ev.target;
        
        // Verificar si existe un elemento de reCAPTCHA
        const recaptchaElement = form.querySelector('.g-recaptcha');
        if (!recaptchaElement) return true;
        
        // Verificar si grecaptcha está disponible
        if (typeof grecaptcha === 'undefined') {
            console.error('La API de reCAPTCHA no está cargada');
            return true; // Permitir el envío para no bloquear al usuario
        }
        
        // Obtener la respuesta de reCAPTCHA
        const recaptchaResponse = grecaptcha.getResponse();
        
        // Si no hay respuesta, prevenir el envío y mostrar error
        if (!recaptchaResponse) {
            ev.preventDefault();
            
            // Buscar o crear contenedor de errores
            let errorContainer = form.querySelector('.recaptcha-error');
            if (!errorContainer) {
                errorContainer = document.createElement('div');
                errorContainer.classList.add('alert', 'alert-danger', 'mt-2', 'recaptcha-error');
                const parentDiv = recaptchaElement.closest('.field-captcha') || recaptchaElement.parentNode;
                parentDiv.appendChild(errorContainer);
            }
            
            // Mostrar mensaje de error
            errorContainer.textContent = 'Por favor, complete el captcha';
            
            return false;
        }
        
        return true;
    },

    /**
     * Inicializar listeners de reCAPTCHA en formularios de registro
     */
    init: function () {
        // Usar una función más robusta para determinar cuando el DOM está listo
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.attachValidators());
        } else {
            this.attachValidators();
        }
    },
    
    attachValidators: function() {
        // Buscar formularios por clase o atributo relevante, no solo por ID
        const signupForms = document.querySelectorAll('form.oe_signup_form, form[action="/web/signup"]');
        
        if (signupForms.length) {
            console.log('Se encontraron', signupForms.length, 'formularios de registro');
            
            signupForms.forEach(form => {
                // Verificar si ya tiene el listener para evitar duplicados
                if (!form.hasRecaptchaValidator) {
                    form.addEventListener('submit', this.validateRecaptcha);
                    form.hasRecaptchaValidator = true;
                    console.log('Validador de reCAPTCHA adjuntado a formulario');
                }
            });
        } else {
            console.log('No se encontraron formularios de registro');
        }
    }
};

// Inicializar el validador
recaptchaValidator.init();

// Para depuración
console.log('Módulo de validación reCAPTCHA cargado');

// Registrarlo como un servicio si es necesario
const recaptchaService = {
    dependencies: [],
    start() {
        return recaptchaValidator;
    },
};

registry.category("services").add("recaptcha_validator", recaptchaService);