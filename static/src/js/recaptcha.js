/** @odoo-module **/

import { registry } from "@web/core/registry";

const turnstileValidator = {
    /**
     * Validar la respuesta de Turnstile antes de enviar el formulario
     * @param {Event} ev - Evento de envío del formulario
     */
    validateTurnstile: function (ev) {
        // Obtener el elemento del formulario
        const form = ev.target;
        
        // Verificar si existe un elemento de Turnstile
        const turnstileElement = form.querySelector('.cf-turnstile');
        if (!turnstileElement) return true;
        
        // Obtener la respuesta de Turnstile
        const turnstileResponse = form.querySelector('[name="cf-turnstile-response"]')?.value;
        
        // Si no hay respuesta, prevenir el envío y mostrar error
        if (!turnstileResponse) {
            ev.preventDefault();
            
            // Buscar o crear contenedor de errores
            let errorContainer = form.querySelector('.turnstile-error');
            if (!errorContainer) {
                errorContainer = document.createElement('div');
                errorContainer.classList.add('alert', 'alert-danger', 'mt-2', 'turnstile-error');
                const parentDiv = turnstileElement.closest('.field-captcha') || turnstileElement.parentNode;
                parentDiv.appendChild(errorContainer);
            }
            
            // Mostrar mensaje de error
            errorContainer.textContent = 'Por favor, complete el captcha';
            
            return false;
        }
        
        return true;
    },

    /**
     * Inicializar listeners para formularios de registro
     */
    init: function () {
        // Usar una función más robusta para determinar cuando el DOM está listo
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.attachValidators());
        } else {
            this.attachValidators();
        }
        
        // Agregar un listener para cuando la página esté completamente cargada
        window.addEventListener('load', () => {
            this.attachValidators();
        });
    },
    
    attachValidators: function() {
        // Buscar formularios por clase o atributo relevante
        const signupForms = document.querySelectorAll('form.oe_signup_form, form[action="/web/signup"]');
        
        if (signupForms.length) {
            console.log('Se encontraron', signupForms.length, 'formularios de registro');
            
            signupForms.forEach(form => {
                // Verificar si ya tiene el listener para evitar duplicados
                if (!form.hasTurnstileValidator) {
                    form.addEventListener('submit', this.validateTurnstile.bind(this));
                    form.hasTurnstileValidator = true;
                    console.log('Validador de Turnstile adjuntado a formulario');
                }
                
                // Verificar si hay elementos de Turnstile
                const turnstileElements = form.querySelectorAll('.cf-turnstile');
                turnstileElements.forEach(element => {
                    console.log('Elemento Turnstile encontrado con data-sitekey:', element.getAttribute('data-sitekey'));
                });
            });
        } else {
            console.log('No se encontraron formularios de registro');
        }
    }
};

// Inicializar el validador
turnstileValidator.init();

// Para depuración
console.log('Módulo de validación Turnstile cargado');

// Registrarlo como un servicio 
const turnstileService = {
    dependencies: [],
    start() {
        return turnstileValidator;
    },
};

registry.category("services").add("turnstile_validator", turnstileService);