/** @odoo-module **/

import { registry } from "@web/core/registry";

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
        if (!recaptchaElement) {
            console.log('No se encontró elemento de reCAPTCHA en el formulario');
            return true;
        }
        
        console.log('Estado del elemento reCAPTCHA:', {
            siteKey: recaptchaElement.getAttribute('data-sitekey'),
            theme: recaptchaElement.getAttribute('data-theme'),
            hasChildren: recaptchaElement.children.length > 0,
            innerHtml: recaptchaElement.innerHTML.slice(0, 100)
        });
        
        // Verificar si grecaptcha está disponible
        if (typeof grecaptcha === 'undefined') {
            console.error('La API de reCAPTCHA no está cargada - intentando cargarla ahora');
            
            // Cargar el script de reCAPTCHA dinámicamente si no está ya
            if (!document.querySelector('script[src*="recaptcha/api.js"]')) {
                const script = document.createElement('script');
                script.src = 'https://www.google.com/recaptcha/api.js';
                script.async = true;
                script.defer = true;
                document.head.appendChild(script);
                console.log('Script de reCAPTCHA agregado dinámicamente');
            }
            
            // No bloquear el envío, pero mostrar alerta
            alert('Por favor, refresque la página e intente nuevamente. El sistema de seguridad no se ha cargado correctamente.');
            return false;
        }
        
        // Obtener la respuesta de reCAPTCHA
        const recaptchaResponse = grecaptcha.getResponse();
        console.log('Respuesta de reCAPTCHA:', recaptchaResponse ? 'presente' : 'ausente');
        
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
            document.addEventListener('DOMContentLoaded', () => {
                this.checkReCaptchaAPI();
                this.attachValidators();
            });
        } else {
            this.checkReCaptchaAPI();
            this.attachValidators();
        }
        
        // Agregar un listener para cuando la página esté completamente cargada
        window.addEventListener('load', () => {
            this.checkReCaptchaAPI();
            this.attachValidators();
        });
    },
    
    checkReCaptchaAPI: function() {
        // Verificar si la API de reCAPTCHA está cargada
        if (typeof grecaptcha === 'undefined') {
            console.warn('API de reCAPTCHA no detectada - verificando elementos');
            
            // Buscar elementos de reCAPTCHA en la página
            const recaptchaElements = document.querySelectorAll('.g-recaptcha');
            if (recaptchaElements.length > 0) {
                console.log('Elementos reCAPTCHA encontrados:', recaptchaElements.length);
                
                // Verificar si el script ya está cargado
                if (!document.querySelector('script[src*="recaptcha/api.js"]')) {
                    console.log('Cargando script de reCAPTCHA dinámicamente');
                    const script = document.createElement('script');
                    script.src = 'https://www.google.com/recaptcha/api.js';
                    script.async = true;
                    script.defer = true;
                    document.head.appendChild(script);
                } else {
                    console.log('Script de reCAPTCHA ya presente en el DOM');
                }
            }
        } else {
            console.log('API de reCAPTCHA detectada');
        }
    },
    
    attachValidators: function() {
        // Buscar formularios por clase o atributo relevante
        const signupForms = document.querySelectorAll('form.oe_signup_form, form[action="/web/signup"]');
        
        if (signupForms.length) {
            console.log('Se encontraron', signupForms.length, 'formularios de registro');
            
            signupForms.forEach(form => {
                // Verificar si ya tiene el listener para evitar duplicados
                if (!form.hasRecaptchaValidator) {
                    form.addEventListener('submit', this.validateRecaptcha.bind(this));
                    form.hasRecaptchaValidator = true;
                    console.log('Validador de reCAPTCHA adjuntado a formulario');
                }
                
                // Verificar si hay elementos de reCAPTCHA sin inicializar
                const recaptchaElements = form.querySelectorAll('.g-recaptcha');
                recaptchaElements.forEach(element => {
                    console.log('Elemento reCAPTCHA encontrado con data-sitekey:', element.getAttribute('data-sitekey'));
                });
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

// Registrarlo como un servicio 
const recaptchaService = {
    dependencies: [],
    start() {
        return recaptchaValidator;
    },
};

registry.category("services").add("recaptcha_validator", recaptchaService);