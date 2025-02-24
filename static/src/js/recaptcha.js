/** @odoo-module **/

import { registry } from "@web/core/registry";

const TurnstileLogger = {
    log: function(message, level = 'info') {
        const timestamp = new Date().toISOString();
        switch(level) {
            case 'error':
                console.error(`[Turnstile] [${timestamp}] ${message}`);
                break;
            case 'warn':
                console.warn(`[Turnstile] [${timestamp}] ${message}`);
                break;
            default:
                console.log(`[Turnstile] [${timestamp}] ${message}`);
        }
    }
};

const turnstileValidator = {
    init: function () {
        TurnstileLogger.log('Inicializando Turnstile Validator');
        
        window.addEventListener("load", () => {
            try {
                this.loadTurnstileScript();
                this.attachValidators();
                TurnstileLogger.log('Inicialización completada con éxito');
            } catch (error) {
                TurnstileLogger.log(`Error en inicialización: ${error}`, 'error');
            }
        });
    },

    loadTurnstileScript: function () {
        TurnstileLogger.log('Intentando cargar script de Turnstile');
        
        const script = document.createElement('script');
        script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
        script.async = true;
        script.defer = true;
        
        script.onload = () => {
            TurnstileLogger.log('Script de Turnstile cargado exitosamente');
        };
        
        script.onerror = (error) => {
            TurnstileLogger.log(`Error cargando script de Turnstile: ${error}`, 'error');
        };
        
        document.head.appendChild(script);
    },

    attachValidators: function () {
        const signupForms = document.querySelectorAll('form.oe_signup_form');
        
        TurnstileLogger.log(`Formularios de registro encontrados: ${signupForms.length}`);
        
        if (!signupForms.length) {
            TurnstileLogger.log('No se encontraron formularios de registro', 'warn');
            return;
        }

        signupForms.forEach((form, index) => {
            if (!form.hasTurnstileValidator) {
                TurnstileLogger.log(`Agregando validador al formulario ${index + 1}`);
                
                form.addEventListener("submit", this.validateTurnstile.bind(this));
                form.hasTurnstileValidator = true;
            }
        });
    },

    validateTurnstile: function (ev) {
        TurnstileLogger.log('Validando Turnstile en envío de formulario');
        
        const form = ev.target;
        const turnstileResponse = document.querySelector('#cf-turnstile-response')?.value;

        if (!turnstileResponse) {
            TurnstileLogger.log('Captcha no completado', 'warn');
            
            ev.preventDefault();
            alert("Por favor, completa el captcha de seguridad antes de enviar el formulario.");
            
            return false;
        }

        TurnstileLogger.log('Validación de Turnstile completada con éxito');
        return true;
    }
};

turnstileValidator.init();

const turnstileService = {
    dependencies: [],
    start() {
        TurnstileLogger.log('Servicio Turnstile iniciado');
        return turnstileValidator;
    },
};

registry.category("services").add("turnstile_validator", turnstileService);

export default turnstileValidator;