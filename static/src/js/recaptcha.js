/** @odoo-module **/
import { registry } from "@web/core/registry";

/**
 * TurnstileHandler - Servicio simplificado para manejar Cloudflare Turnstile
 */
const TurnstileHandler = {
    /**
     * Inicializa el controlador
     */
    init: function() {
        console.log("[Turnstile] Iniciando servicio...");
        
        // Registrar callback global para Turnstile
        window.onTurnstileReady = () => {
            console.log("[Turnstile] API de Turnstile lista");
            this.renderCaptcha();
        };
        
        // Cargar script si es necesario
        this.loadScript();
        
        // Configurar validación cuando el DOM esté listo
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", () => this.setupForm());
        } else {
            this.setupForm();
        }
    },
    
    /**
     * Carga el script de Turnstile
     */
    loadScript: function() {
        if (document.querySelector('script[src*="turnstile/v0/api.js"]')) {
            console.log("[Turnstile] Script ya cargado");
            return;
        }
        
        console.log("[Turnstile] Cargando script...");
        const script = document.createElement("script");
        script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onTurnstileReady&render=explicit";
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
    },
    
    /**
     * Configura el formulario para validación
     */
    setupForm: function() {
        const form = document.querySelector("form.oe_signup_form");
        if (!form || form.dataset.turnstileValidatorAttached === "true") {
            return;
        }
        
        // Adjuntar validador al formulario
        form.addEventListener("submit", (e) => this.validateForm(e));
        form.dataset.turnstileValidatorAttached = "true";
        console.log("[Turnstile] Validador adjuntado al formulario");
        
        // Verificar si necesitamos renderizar el captcha
        setTimeout(() => {
            const container = document.querySelector(".cf-turnstile");
            if (container && !container.querySelector("iframe")) {
                this.renderCaptcha();
            }
        }, 500);
    },
    
    /**
     * Renderiza el captcha explícitamente
     */
    renderCaptcha: function() {
        if (!window.turnstile) {
            console.log("[Turnstile] API de Turnstile no disponible aún");
            return;
        }
        
        const container = document.querySelector(".cf-turnstile");
        if (!container) {
            console.warn("[Turnstile] No se encontró el contenedor del captcha");
            return;
        }
        
        const sitekey = container.getAttribute("data-sitekey");
        if (!sitekey) {
            console.error("[Turnstile] No se encontró el sitekey");
            return;
        }
        
        // Limpiar contenedor existente
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
        
        // Renderizar captcha
        try {
            console.log("[Turnstile] Renderizando captcha con sitekey:", sitekey);
            window.turnstile.render(container, {
                sitekey: sitekey,
                callback: (token) => {
                    console.log("[Turnstile] Token generado");
                    const input = document.querySelector('input[name="cf-turnstile-response"]');
                    if (input) {
                        input.value = token;
                    }
                }
            });
        } catch (error) {
            console.error("[Turnstile] Error al renderizar:", error);
        }
    },
    
    /**
     * Valida el formulario al enviar
     */
    validateForm: function(e) {
        const response = document.querySelector('input[name="cf-turnstile-response"]')?.value;
        if (!response) {
            e.preventDefault();
            const captchaField = document.querySelector(".field-captcha");
            if (captchaField) {
                let errorContainer = captchaField.querySelector(".alert");
                if (!errorContainer) {
                    errorContainer = document.createElement("div");
                    errorContainer.className = "alert alert-danger mt-2";
                    captchaField.appendChild(errorContainer);
                }
                errorContainer.textContent = "Por favor, completa la verificación de seguridad.";
            }
        }
    }
};

// Inicializar el servicio
setTimeout(() => TurnstileHandler.init(), 100);

// Registrar el servicio en Odoo
registry.category("services").add("turnstile_handler", {
    dependencies: [],
    start() {
        console.log("[Turnstile] Servicio registrado");
        return TurnstileHandler;
    }
});

export default TurnstileHandler;