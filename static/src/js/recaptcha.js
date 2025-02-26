/** @odoo-module **/
import { registry } from "@web/core/registry";

// Evitar inicialización múltiple
if (window._turnstileInitialized) {
    console.log("[Turnstile] Ya inicializado, evitando doble carga");
} else {
    window._turnstileInitialized = true;

    (function () {
        function cleanupDuplicateCaptchas() {
            const containers = document.querySelectorAll(".cf-turnstile");
            if (containers.length <= 1) return;

            console.log("[Turnstile] Eliminando " + (containers.length - 1) + " captchas duplicados.");

            // Mantener solo el primer CAPTCHA y eliminar los demás
            for (let i = 1; i < containers.length; i++) {
                if (containers[i].parentNode) {
                    containers[i].parentNode.removeChild(containers[i]);
                }
            }
        }

        // Ejecutar la limpieza en diferentes momentos
        if (document.readyState !== "loading") cleanupDuplicateCaptchas();
        document.addEventListener("DOMContentLoaded", cleanupDuplicateCaptchas);
        window.addEventListener("load", cleanupDuplicateCaptchas);

        // Limpiar captchas duplicados periódicamente durante unos segundos
        let attempts = 0;
        const cleanupInterval = setInterval(() => {
            cleanupDuplicateCaptchas();
            if (++attempts >= 10) clearInterval(cleanupInterval);
        }, 500);

        // Observar cambios en el DOM para eliminar captchas insertados dinámicamente
        if (typeof MutationObserver !== "undefined") {
            const observer = new MutationObserver((mutations) => {
                let shouldCleanup = false;
                for (const mutation of mutations) {
                    if (mutation.type === "childList") {
                        for (const node of mutation.addedNodes) {
                            if (node.nodeType === 1 && (node.classList?.contains("cf-turnstile") || node.querySelector?.(".cf-turnstile"))) {
                                shouldCleanup = true;
                                break;
                            }
                        }
                    }
                    if (shouldCleanup) break;
                }
                if (shouldCleanup) cleanupDuplicateCaptchas();
            });

            observer.observe(document.documentElement || document.body, {
                childList: true,
                subtree: true
            });

            window._turnstileObserver = observer;
        }
    })();
}

// Controlar estado de renderización
let turnstileRendered = false;

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
        this.removeDuplicates();

        // Evitar renderizado si ya existe un iframe
        if (document.querySelector(".cf-turnstile iframe")) {
            console.log("[Turnstile] CAPTCHA ya renderizado.");
            turnstileRendered = true;
            return;
        }

        this.loadTurnstileScript();
        this.attachValidator();
    },

    removeDuplicates: function () {
        const containers = document.querySelectorAll(".cf-turnstile");
        if (containers.length <= 1) return;

        console.log("[Turnstile] Eliminando captchas duplicados...");

        for (let i = 1; i < containers.length; i++) {
            if (containers[i].parentNode) {
                containers[i].parentNode.removeChild(containers[i]);
            }
        }
    },

    loadTurnstileScript: function () {
        if (document.querySelector('script[src*="turnstile/v0/api.js"]')) {
            console.log("[Turnstile] Script ya cargado");
            this.waitForTurnstileAPI();
            return;
        }

        console.log("[Turnstile] Cargando script Turnstile...");
        const script = document.createElement("script");
        script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
        script.async = true;
        script.defer = true;
        script.onload = () => {
            console.log("[Turnstile] Script cargado correctamente");
            this.waitForTurnstileAPI();
        };
        document.head.appendChild(script);
    },

    waitForTurnstileAPI: function () {
        let attempts = 0;
        const maxAttempts = 20;

        const checkAPI = () => {
            if (typeof window.turnstile !== "undefined") {
                this.renderTurnstile();
            } else if (++attempts < maxAttempts) {
                setTimeout(checkAPI, 250);
            } else {
                console.error("[Turnstile] API no disponible después de varios intentos");
            }
        };

        checkAPI();
    },

    renderTurnstile: function () {
        if (turnstileRendered || document.querySelector(".cf-turnstile iframe")) {
            console.log("[Turnstile] CAPTCHA ya renderizado.");
            return;
        }

        this.removeDuplicates();

        const container = document.querySelector(".cf-turnstile");
        if (!container) {
            console.warn("[Turnstile] Contenedor no encontrado.");
            return;
        }

        if (!container.id) {
            container.id = "cf-turnstile-container";
        }

        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }

        console.log("[Turnstile] Renderizando CAPTCHA...");

        try {
            turnstileRendered = true;
            window.turnstile.render(container, {
                sitekey: "0x4AAAAAAA-dpmO_dMh_oBeK",
                theme: "light",
                callback: (token) => {
                    console.log("[Turnstile] Token generado.");
                    const responseField = document.getElementById("cf-turnstile-response");
                    if (responseField) {
                        responseField.value = token;
                    } else {
                        const hiddenField = document.createElement("input");
                        hiddenField.type = "hidden";
                        hiddenField.id = "cf-turnstile-response";
                        hiddenField.name = "cf-turnstile-response";
                        hiddenField.value = token;
                        container.appendChild(hiddenField);
                    }
                },
                "error-callback": () => {
                    console.error("[Turnstile] Error al generar token");
                }
            });
        } catch (error) {
            console.error("[Turnstile] Error al renderizar:", error);
            turnstileRendered = false;
        }
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
                const previousError = captchaField.querySelector(".alert");
                if (previousError) previousError.remove();

                const errorContainer = document.createElement("div");
                errorContainer.className = "alert alert-danger mt-2";
                errorContainer.textContent = "Por favor, completa la verificación de seguridad.";
                captchaField.appendChild(errorContainer);
            } else {
                alert("Completa la verificación antes de continuar.");
            }
            return false;
        }
        return true;
    }
};

// Inicializar
setTimeout(() => TurnstileValidator.init(), 100);

registry.category("services").add("turnstile_validator", {
    dependencies: [],
    start() {
        console.log("[Turnstile] Servicio iniciado");
        return TurnstileValidator;
    },
});

export default TurnstileValidator;
