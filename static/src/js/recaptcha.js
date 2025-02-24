/** @odoo-module **/

import { registry } from "@web/core/registry";

const turnstileValidator = {
    init: function () {
        window.addEventListener("load", () => {
            if (typeof turnstile !== "undefined") {
                turnstile.render(".cf-turnstile");
            }
        });

        this.attachValidators();
    },
    
    attachValidators: function () {
        const signupForms = document.querySelectorAll('form[action="/web/signup"]');
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
        const turnstileResponse = form.querySelector('[name="cf-turnstile-response"]')?.value;

        if (!turnstileResponse) {
            ev.preventDefault();
            alert("Por favor, completa el captcha.");
            return false;
        }

        return true;
    }
};

turnstileValidator.init();
console.log("Turnstile Validator cargado");

const turnstileService = {
    dependencies: [],
    start() {
        return turnstileValidator;
    },
};

registry.category("services").add("turnstile_validator", turnstileService);
