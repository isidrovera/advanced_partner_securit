/** @odoo-module **/
import { registry } from "@web/core/registry";

/**
 * TurnstileValidator - Servicio para manejar la validación de Cloudflare Turnstile en Odoo
 * Solución que resuelve problemas de CSP y scope
 */
const TurnstileValidator = {
    // Configuración de Turnstile
    config: {
        scriptSrc: "https://challenges.cloudflare.com/turnstile/v0/api.js",
        containerSelector: ".cf-turnstile, #cf-turnstile-container",
        formSelector: "form.oe_signup_form",
        responseInputSelector: 'input[name="cf-turnstile-response"]',
        loadingDelay: 500,  // ms para esperar antes de verificar el renderizado
    },

    /**
     * Inicializa el validador
     */
    init: function() {
        console.log("[Turnstile] Iniciando validación...");

        // Registrar la función global para Turnstile antes de cargar el script
        window.onTurnstileReady = () => {
            console.log("[Turnstile] Turnstile API lista para usar");
            this.renderCaptchas();
        };

        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", () => this.setup());
        } else {
            this.setup();
        }
    },

    /**
     * Configura el validador
     */
    setup: function() {
        // Cargar el script de Turnstile si aún no está cargado
        this.loadTurnstileScript();
        
        // Adjuntar el validador al formulario
        this.attachValidator();
        
        // Esperar un tiempo para verificar si el CAPTCHA se renderizó
        setTimeout(() => {
            this.checkCaptchaRendering();
        }, this.config.loadingDelay);
    },

    /**
     * Carga el script de Turnstile
     */
    loadTurnstileScript: function() {
        if (document.querySelector(`script[src*="turnstile/v0/api.js"]`)) {
            console.log("[Turnstile] Script ya cargado.");
            return;
        }

        console.log("[Turnstile] Cargando script...");
        const script = document.createElement("script");
        script.src = `${this.config.scriptSrc}?onload=onTurnstileReady&render=explicit`;
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
    },

    /**
     * Renderiza manualmente los CAPTCHAs en la página
     */
    renderCaptchas: function() {
        if (!window.turnstile) {
            console.error("[Turnstile] API de Turnstile no disponible");
            return;
        }

        const containers = document.querySelectorAll(this.config.containerSelector);
        if (containers.length === 0) {
            console.warn("[Turnstile] No se encontraron contenedores de CAPTCHA");
            return;
        }

        // Limpiar contenedores para evitar duplicados
        containers.forEach((container, index) => {
            // Mantener solo el primer contenedor, eliminar los demás
            if (index > 0) {
                container.remove();
                return;
            }

            // Limpiar el contenido del primer contenedor
            while (container.firstChild) {
                container.removeChild(container.firstChild);
            }

            // Obtener el sitekey del atributo data-sitekey
            const sitekey = container.getAttribute("data-sitekey");
            if (!sitekey) {
                console.error("[Turnstile] No se encontró el atributo data-sitekey");
                return;
            }

            // Renderizar el captcha explícitamente
            try {
                console.log(`[Turnstile] Renderizando CAPTCHA con sitekey: ${sitekey}`);
                window.turnstile.render(container, {
                    sitekey: sitekey,
                    callback: (token) => {
                        console.log("[Turnstile] Token generado");
                        const responseInput = document.querySelector(this.config.responseInputSelector);
                        if (responseInput) {
                            responseInput.value = token;
                        }
                    },
                });
            } catch (error) {
                console.error("[Turnstile] Error al renderizar:", error);
            }
        });
    },

    /**
     * Verifica si el CAPTCHA se ha renderizado correctamente
     */
    checkCaptchaRendering: function() {
        const container = document.querySelector(this.config.containerSelector);
        if (!container) {
            console.warn("[Turnstile] No se encontró el contenedor del CAPTCHA.");
            return;
        }

        const iframe = container.querySelector("iframe");
        if (!iframe) {
            console.warn("[Turnstile] CAPTCHA no renderizado. Intentando renderizar manualmente...");
            this.renderCaptchas();
        } else {
            console.log("[Turnstile] CAPTCHA renderizado correctamente.");
        }
    },

    /**
     * Adjunta el validador al formulario
     */
    attachValidator: function() {
        const form = document.querySelector(this.config.formSelector);
        if (!form || form.dataset.turnstileValidatorAttached === "true") return;

        form.addEventListener("submit", this.validateTurnstile.bind(this));
        form.dataset.turnstileValidatorAttached = "true";
        console.log("[Turnstile] Validador adjuntado al formulario.");
    },

    /**
     * Valida la respuesta de Turnstile al enviar el formulario
     */
    validateTurnstile: function(ev) {
        const turnstileResponse = document.querySelector(this.config.responseInputSelector)?.value;
        if (!turnstileResponse) {
            ev.preventDefault();
            const captchaField = document.querySelector(".field-captcha");
            if (captchaField) {
                let errorContainer = captchaField.querySelector(".alert");
                if (!errorContainer) {
                    errorContainer = document.createElement("div");
                    errorContainer.className = "alert alert-danger mt-2";
                    captchaField.appendChild(errorContainer);
                }
                errorContainer.textContent = "Por favor, completa la verificación de seguridad.";
            } else {
                alert("Completa la verificación antes de continuar.");
            }
            return false;
        }
        return true;
    }
};

// Inicializar el validador después de cargar la página
setTimeout(() => TurnstileValidator.init(), 500);

// Registrar el servicio en Odoo
registry.category("services").add("turnstile_validator", {
    dependencies: [],
    start() {
        console.log("[Turnstile] Servicio iniciado.");
        return TurnstileValidator;
    },
});

export default TurnstileValidator;