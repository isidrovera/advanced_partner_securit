/** @odoo-module **/
import { registry } from "@web/core/registry";

// Evitar doble inicialización
if (window._turnstileInitialized) {
    console.log("[Turnstile] Ya inicializado.");
} else {
    window._turnstileInitialized = true;

    // Función para eliminar captchas duplicados
    function removeDuplicateCaptchas() {
        const containers = document.querySelectorAll(".cf-turnstile");
        if (containers.length > 1) {
            console.log(`[Turnstile] Eliminando ${containers.length - 1} captchas duplicados.`);
            for (let i = 1; i < containers.length; i++) {
                containers[i].remove();
            }
        }
    }

    // Observar cambios en el DOM para evitar duplicaciones
    const observer = new MutationObserver(() => {
        removeDuplicateCaptchas();
    });

    observer.observe(document.body, { childList: true, subtree: true });
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
        // Verificar si la función está definida
        if (typeof removeDuplicateCaptchas === "function") {
            removeDuplicateCaptchas();
        } else {
            console.error("[Turnstile] La función removeDuplicateCaptchas no está definida.");
        }

        // Verificar si el CAPTCHA ya está en el formulario
        const captchaContainer = document.querySelector(".cf-turnstile");
        if (!captchaContainer) {
            console.warn("[Turnstile] No se encontró el contenedor del CAPTCHA.");
            return;
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
