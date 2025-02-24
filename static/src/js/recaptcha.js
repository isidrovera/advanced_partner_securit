/** @odoo-module **/

import { registry } from "@web/core/registry";

const turnstileValidator = {
    init: function () {
        window.addEventListener("load", () => {
            this.loadTurnstileScript();
            this.attachValidators();
        });
    },

    loadTurnstileScript: function () {
        const script = document.createElement('script');
        script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
        script.async = true;
        script.defer = true;
        document.head.appendChild(script);
    },

    attachValidators: function () {
        const signupForms = document.querySelectorAll('form.oe_signup_form');
        if (!signupForms.length) return;

        signupForms.forEach(form => {
            if (!form.hasTurnstileValidator) {
                form.addEventListener("submit", this.validateTurnstile.bind(this));
                form.hasTurnstileValidator = true;
            }
        });
    },

    validateTurnstile: function (ev) {
        const form = ev.target;
        const turnstileResponse = document.querySelector('[name="cf-turnstile-response"]')?.value;

        if (!turnstileResponse) {
            ev.preventDefault();
            alert("Por favor, completa el captcha antes de enviar el formulario.");
            return false;
        }

        return true;
    }
};

turnstileValidator.init();

const turnstileService = {
    dependencies: [],
    start() {
        return turnstileValidator;
    },
};

registry.category("services").add("turnstile_validator", turnstileService);