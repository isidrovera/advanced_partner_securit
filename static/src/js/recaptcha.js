/** @odoo-module **/

import { registry } from "@web/core/registry";

const TurnstileValidator = {
    init: function () {
        document.addEventListener("DOMContentLoaded", () => {
            this.loadTurnstileScript();
            this.renderTurnstile();
            this.attachValidator();
        });
    },

    loadTurnstileScript: function () {
        if (document.querySelector('script[src="https://challenges.cloudflare.com/turnstile/v0/api.js"]')) {
            return;
        }
        const script = document.createElement("script");
        script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
    },

    renderTurnstile: function () {
        const container = document.querySelector(".cf-turnstile");
        if (!container) return;
        if (typeof turnstile !== "undefined") {
            turnstile.render(container, {
                sitekey: "0x4AAAAAAA-dpmO_dMh_oBeK",
                theme: "light",
                callback: (token) => {
                    console.log("[Turnstile] Token generado:", token);
                    document.querySelector('#cf-turnstile-response').value = token;
                },
                errorCallback: () => {
                    console.error("[Turnstile] Error al generar el token");
                }
            });
        } else {
            console.warn("[Turnstile] La librería no está cargada correctamente.");
        }
    },

    attachValidator: function () {
        const form = document.querySelector("form.oe_signup_form");
        if (!form) return;
        form.addEventListener("submit", this.validateTurnstile.bind(this));
    },

    validateTurnstile: function (ev) {
        const turnstileResponse = document.querySelector('#cf-turnstile-response')?.value;
        if (!turnstileResponse) {
            ev.preventDefault();
            alert("Por favor, completa el captcha antes de enviar el formulario.");
            return false;
        }
        return true;
    }
};

TurnstileValidator.init();

const turnstileService = {
    dependencies: [],
    start() {
        return TurnstileValidator;
    },
};

registry.category("services").add("turnstile_validator", turnstileService);

export default TurnstileValidator;