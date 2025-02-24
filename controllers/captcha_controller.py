/** @odoo-module **/

import { registry } from "@web/core/registry";

const TurnstileValidator = {
    init: function () {
        console.log("[Turnstile] Iniciando validación de Turnstile...");
        document.addEventListener("DOMContentLoaded", () => {
            console.log("[Turnstile] DOM completamente cargado, inicializando...");
            this.loadTurnstileScript();
        });
    },

    loadTurnstileScript: function () {
        console.log("[Turnstile] Intentando cargar el script...");

        if (document.querySelector('script[src="https://challenges.cloudflare.com/turnstile/v0/api.js"]')) {
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
        console.log("[Turnstile] Buscando contenedor para renderizar el captcha...");
        const container = document.querySelector(".cf-turnstile");
        if (!container) {
            console.warn("[Turnstile] No se encontró el contenedor de Turnstile en el formulario.");
            return;
        }

        console.log("[Turnstile] Renderizando Turnstile en el contenedor.");
        if (typeof turnstile !== "undefined") {
            turnstile.render(container, {
                sitekey: "0x4AAAAAAA-dpmO_dMh_oBeK",
                theme: "light",
                callback: (token) => {
                    console.log("[Turnstile] Token generado exitosamente:", token);
                    document.querySelector('#cf-turnstile-response').value = token;
                },
                errorCallback: () => {
                    console.error("[Turnstile] Error al generar el token de Turnstile.");
                }
            });
        } else {
            console.warn("[Turnstile] La librería Turnstile no está disponible en el entorno actual.");
        }
    }
};

TurnstileValidator.init();

const turnstileService = {
    dependencies: [],
    start() {
        console.log("[Turnstile] Servicio Turnstile iniciado correctamente.");
        return TurnstileValidator;
    },
};

registry.category("services").add("turnstile_validator", turnstileService);

export default TurnstileValidator;
