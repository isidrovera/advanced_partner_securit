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
        
        document.addEventListener("DOMContentLoaded", () => {
            try {
                this.loadTurnstileScript();
                this.setupTurnstileRendering();
                this.attachValidators();
                TurnstileLogger.log('Inicialización completada con éxito');
            } catch (error) {
                TurnstileLogger.log(`Error en inicialización: ${error}`, 'error');
            }
        });
    },

    loadTurnstileScript: function () {
        TurnstileLogger.log('Intentando cargar script de Turnstile');
        
        // Verificar si el script ya está cargado
        if (document.querySelector('script[src="https://challenges.cloudflare.com/turnstile/v0/api.js"]')) {
            TurnstileLogger.log('Script de Turnstile ya cargado');
            return;
        }

        const script = document.createElement('script');
        script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
        script.async = true;
        script.defer = true;
        
        script.onload = () => {
            TurnstileLogger.log('Script de Turnstile cargado exitosamente');
            this.renderTurnstile();
        };
        
        script.onerror = (error) => {
            TurnstileLogger.log(`Error cargando script de Turnstile: ${error}`, 'error');
        };
        
        document.head.appendChild(script);
    },

    setupTurnstileRendering: function() {
        // Implementar renderización manual con múltiples intentos
        this.renderAttempts = 0;
        this.maxRenderAttempts = 5;
    },

    renderTurnstile: function() {
        const container = document.querySelector('#cf-turnstile-container');
        
        if (!container) {
            TurnstileLogger.log('Contenedor de Turnstile no encontrado', 'warn');
            return;
        }

        // Verificar si Turnstile ya está renderizado
        if (container.querySelector('.cf-turnstile-widget')) {
            TurnstileLogger.log('Turnstile ya renderizado', 'info');
            return;
        }

        try {
            // Verificar si la función turnstile está disponible
            if (typeof turnstile !== 'undefined') {
                turnstile.render('#cf-turnstile-container', {
                    sitekey: "0x4AAAAAAA-dpmO_dMh_oBeK",
                    theme: "light",
                    callback: (token) => {
                        // Establecer el valor del token en un campo oculto
                        const hiddenInput = document.querySelector('#cf-turnstile-response');
                        if (hiddenInput) {
                            hiddenInput.value = token;
                        }
                    }
                });
                TurnstileLogger.log('Turnstile renderizado exitosamente');
            } else {
                this.retryRenderTurnstile();
            }
        } catch (error) {
            TurnstileLogger.log(`Error renderizando Turnstile: ${error}`, 'error');
            this.retryRenderTurnstile();
        }
    },

    retryRenderTurnstile: function() {
        this.renderAttempts++;
        
        if (this.renderAttempts < this.maxRenderAttempts) {
            TurnstileLogger.log(`Reintentando renderización (Intento ${this.renderAttempts})`, 'warn');
            setTimeout(() => this.renderTurnstile(), 1000 * this.renderAttempts);
        } else {
            TurnstileLogger.log('Máximo de intentos de renderización alcanzado', 'error');
        }
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