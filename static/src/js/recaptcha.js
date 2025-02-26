/** @odoo-module **/
import { registry } from "@web/core/registry";

// Namespace global para las funciones de Turnstile
window._TurnstileHelper = window._TurnstileHelper || {
    removeDuplicateCaptchas: function() {
        const containers = document.querySelectorAll(".cf-turnstile");
        if (containers.length > 1) {
            console.log(`[Turnstile] Eliminando ${containers.length - 1} CAPTCHA(s) duplicado(s).`);
            for (let i = 1; i < containers.length; i++) {
                containers[i].remove();
            }
        }
    },
    
    // Cargar el script de Turnstile de manera segura (respetando CSP)
    loadTurnstileScript: function() {
        if (document.querySelector('script[src*="turnstile/v0/api.js"]')) {
            console.log("[Turnstile] Script ya cargado.");
            return;
        }

        console.log("[Turnstile] Cargando script...");
        const script = document.createElement("script");
        script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onTurnstileLoad";
        script.async = true;
        script.defer = true;
        
        // Agregar onload callback como una función global para evitar problemas de CSP
        window.onTurnstileLoad = function() {
            console.log("[Turnstile] Script cargado correctamente y listo para renderizar.");
            // Si hay un elemento turnstile presente, podemos forzar el renderizado
            const turnstileContainers = document.querySelectorAll(".cf-turnstile");
            if (turnstileContainers.length > 0) {
                console.log("[Turnstile] Forzando renderizado de captchas encontrados.");
                // El renderizado se manejará automáticamente por Turnstile
            }
        };
        
        document.head.appendChild(script);
    }
};

// Inicializar solo una vez
if (!window._turnstileInitialized) {
    window._turnstileInitialized = true;

    // Observar cambios en el DOM para evitar CAPTCHA duplicado
    const observer = new MutationObserver(() => {
        if (window._TurnstileHelper && typeof window._TurnstileHelper.removeDuplicateCaptchas === "function") {
            window._TurnstileHelper.removeDuplicateCaptchas();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // Cargar el script de Turnstile
    if (window._TurnstileHelper && typeof window._TurnstileHelper.loadTurnstileScript === "function") {
        window._TurnstileHelper.loadTurnstileScript();
    }
}

const TurnstileValidator = {
    init: function () {
        console.log("[Turnstile] Iniciando validación...");

        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", () => this.setup());
        } else {
            this.setup();
        }
    },

    setup: function () {
        // Usar la función desde el namespace global
        if (window._TurnstileHelper && typeof window._TurnstileHelper.removeDuplicateCaptchas === "function") {
            window._TurnstileHelper.removeDuplicateCaptchas();
        } else {
            console.error("[Turnstile] La función removeDuplicateCaptchas no está disponible en el namespace global.");
        }

        // Verificar si el CAPTCHA ya está en el formulario
        const captchaContainer = document.querySelector(".cf-turnstile");
        if (!captchaContainer) {
            console.warn("[Turnstile] No se encontró el contenedor del CAPTCHA.");
            return;
        }

        // Revisar si el CAPTCHA ya se ha cargado
        if (!captchaContainer.querySelector("iframe")) {
            console.warn("[Turnstile] No se ha renderizado el CAPTCHA. Verifica el sitio clave.");
        }

        this.attachValidator();
    },

    attachValidator: function () {
        const form = document.querySelector("form.oe_signup_form");
        if (!form || form.dataset.turnstileValidatorAttached === "true") return;

        form.addEventListener("submit", this.validateTurnstile.bind(this));
        form.dataset.turnstileValidatorAttached = "true";
        console.log("[Turnstile] Validador adjuntado al formulario.");
    },

    validateTurnstile: function (ev) {
        const turnstileResponse = document.querySelector('input[name="cf-turnstile-response"]')?.value;
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

// Inicializar solo validación
setTimeout(() => TurnstileValidator.init(), 300); // Aumentado el tiempo para asegurar que la página esté completamente cargada

registry.category("services").add("turnstile_validator", {
    dependencies: [],
    start() {
        console.log("[Turnstile] Servicio iniciado.");
        return TurnstileValidator;
    },
});

export default TurnstileValidator;