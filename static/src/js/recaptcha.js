/** @odoo-module **/
import { registry } from "@web/core/registry";

// Variable global para evitar múltiples renderizaciones
let turnstileRendered = false;

const TurnstileValidator = {
    init: function () {
        console.log("[Turnstile] Iniciando validación de Turnstile...");
        
        // Verificar si el DOM ya está cargado
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", () => {
                console.log("[Turnstile] DOM completamente cargado, inicializando...");
                this.setup();
            });
        } else {
            // El DOM ya está cargado
            console.log("[Turnstile] DOM ya está cargado, inicializando inmediatamente...");
            this.setup();
        }
    },
    
    setup: function() {
        // Si ya hay un widget visible, no inicializar de nuevo
        if (document.querySelector('.cf-turnstile iframe')) {
            console.log("[Turnstile] Widget ya visible en el DOM, no se inicializa de nuevo");
            return;
        }
        
        this.loadTurnstileScript();
        this.attachValidator();
    },
    
    loadTurnstileScript: function () {
        console.log("[Turnstile] Intentando cargar el script...");
        if (document.querySelector('script[src*="turnstile/v0/api.js"]')) {
            console.log("[Turnstile] El script ya está cargado.");
            this.renderTurnstile();
            return;
        }
        
        const script = document.createElement("script");
        script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
        script.async = true;
        script.defer = true;
        script.onload = () => {
            console.log("[Turnstile] Script cargado correctamente.");
            this.renderTurnstile();
        };
        script.onerror = () => {
            console.error("[Turnstile] Error al cargar el script de Turnstile.");
        };
        document.head.appendChild(script);
    },
    
    renderTurnstile: function () {
        // Evitar renderizar múltiples veces
        if (turnstileRendered) {
            console.log("[Turnstile] Widget ya renderizado, saltando renderización");
            return;
        }
        
        console.log("[Turnstile] Buscando contenedor para renderizar el captcha...");
        const container = document.getElementById("cf-turnstile-container");
        
        if (!container) {
            console.warn("[Turnstile] No se encontró el contenedor de Turnstile en el formulario.");
            return;
        }
        
        // Limpiar cualquier contenido existente para evitar duplicación
        const existingIframes = container.querySelectorAll('iframe');
        if (existingIframes.length > 0) {
            console.log("[Turnstile] Eliminando iframes existentes:", existingIframes.length);
            existingIframes.forEach(iframe => iframe.remove());
        }
        
        console.log("[Turnstile] Comprobando disponibilidad de la API Turnstile...");
        
        // Esperar a que turnstile esté disponible
        const checkTurnstile = () => {
            if (typeof window.turnstile !== "undefined") {
                console.log("[Turnstile] API disponible, renderizando widget...");
                
                // Marcar como renderizado
                turnstileRendered = true;
                
                window.turnstile.render(container, {
                    sitekey: "0x4AAAAAAA-dpmO_dMh_oBeK",
                    theme: "light",
                    callback: (token) => {
                        console.log("[Turnstile] Token generado exitosamente:", token);
                        document.getElementById('cf-turnstile-response').value = token;
                    },
                    "error-callback": () => {
                        console.error("[Turnstile] Error al generar el token de Turnstile.");
                    }
                });
            } else {
                console.log("[Turnstile] API aún no disponible, reintentando en 100ms...");
                setTimeout(checkTurnstile, 100);
            }
        };
        
        checkTurnstile();
    },
    
    attachValidator: function () {
        console.log("[Turnstile] Buscando formulario para validación...");
        const form = document.querySelector("form.oe_signup_form");
        
        if (!form) {
            console.warn("[Turnstile] No se encontró el formulario 'oe_signup_form'");
            return;
        }
        
        // Evitar agregar múltiples listeners
        if (form.dataset.turnstileValidatorAttached === "true") {
            console.log("[Turnstile] El validador ya está adjunto al formulario");
            return;
        }
        
        console.log("[Turnstile] Formulario encontrado, añadiendo validador...");
        form.addEventListener("submit", this.validateTurnstile.bind(this));
        
        // Marcar el formulario como ya procesado
        form.dataset.turnstileValidatorAttached = "true";
    },
    
    validateTurnstile: function (ev) {
        console.log("[Turnstile] Validando formulario antes de enviar...");
        const turnstileResponse = document.getElementById('cf-turnstile-response')?.value;
        
        if (!turnstileResponse) {
            console.warn("[Turnstile] No se encontró el token de respuesta en el formulario");
            ev.preventDefault();
            
            // Mostrar mensaje de error
            const errorContainer = document.createElement('div');
            errorContainer.className = 'alert alert-danger mt-2';
            errorContainer.textContent = 'Por favor, completa el captcha antes de enviar el formulario.';
            errorContainer.setAttribute('role', 'alert');
            
            const captchaField = document.querySelector('.field-captcha');
            if (captchaField) {
                // Eliminar cualquier mensaje de error anterior
                const previousError = captchaField.querySelector('.alert');
                if (previousError) {
                    previousError.remove();
                }
                
                captchaField.appendChild(errorContainer);
            } else {
                alert("Por favor, completa el captcha antes de enviar el formulario.");
            }
            
            return false;
        }
        
        console.log("[Turnstile] Formulario validado correctamente");
        return true;
    }
};

// Iniciar el validador
TurnstileValidator.init();

// Registrar el servicio para Odoo
const turnstileService = {
    dependencies: [],
    start() {
        console.log("[Turnstile] Servicio Turnstile iniciado correctamente.");
        return TurnstileValidator;
    },
};

registry.category("services").add("turnstile_validator", turnstileService);

export default TurnstileValidator;