/** @odoo-module **/
import { registry } from "@web/core/registry";

// Create a namespace for our Turnstile functionality to avoid scope issues
window._TurnstileHelper = window._TurnstileHelper || {
    // Function to remove duplicate captchas - accessible through the namespace
    removeDuplicateCaptchas: function() {
        const containers = document.querySelectorAll(".cf-turnstile");
        if (containers.length > 1) {
            console.log(`[Turnstile] Eliminando ${containers.length - 1} CAPTCHA(s) duplicado(s).`);
            for (let i = 1; i < containers.length; i++) {
                containers[i].remove();
            }
        }
    },
    
    // Load the Turnstile script
    loadTurnstileScript: function() {
        if (document.querySelector('script[src*="turnstile/v0/api.js"]')) {
            console.log("[Turnstile] Script ya cargado.");
            return;
        }

        console.log("[Turnstile] Cargando script...");
        const script = document.createElement("script");
        script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
        script.async = true;
        script.defer = true;
        script.onload = () => {
            console.log("[Turnstile] Script cargado correctamente.");
        };
        document.head.appendChild(script);
    }
};

// Initialize only once
if (!window._turnstileInitialized) {
    window._turnstileInitialized = true;

    // Observe DOM changes to prevent duplicate CAPTCHAs
    const observer = new MutationObserver(() => window._TurnstileHelper.removeDuplicateCaptchas());
    observer.observe(document.body, { childList: true, subtree: true });

    // Load the Turnstile script
    window._TurnstileHelper.loadTurnstileScript();
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
        // Use the function from the global namespace
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
setTimeout(() => TurnstileValidator.init(), 100);

registry.category("services").add("turnstile_validator", {
    dependencies: [],
    start() {
        console.log("[Turnstile] Servicio iniciado.");
        return TurnstileValidator;
    },
});

export default TurnstileValidator;