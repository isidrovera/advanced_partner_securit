/** @odoo-module **/

import { registry } from "@web/core/registry";

export const recaptchaValidator = {
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
        
        // Obtener la respuesta de reCAPTCHA
        const recaptchaResponse = grecaptcha.getResponse();
        
        // Si no hay respuesta, prevenir el envío y mostrar error
        if (!recaptchaResponse) {
            ev.preventDefault();
            
            // Buscar o crear contenedor de errores
            let errorContainer = form.querySelector('.recaptcha-error');
            if (!errorContainer) {
                errorContainer = document.createElement('div');
                errorContainer.classList.add('alert', 'alert-danger', 'recaptcha-error');
                recaptchaElement.after(errorContainer);
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
        document.addEventListener('DOMContentLoaded', () => {
            // Seleccionar todos los formularios de registro
            const signupForms = document.querySelectorAll('#signup');
            
            signupForms.forEach(form => {
                form.addEventListener('submit', this.validateRecaptcha);
            });
        });
    }
};

// Inicializar el validador cuando el módulo se carga
recaptchaValidator.init();

// Registrar en el registro de Odoo (opcional, pero puede ser útil)
registry.category("web_tour.tours").add("recaptcha_validation", {
    test: true,
    steps: () => []
});