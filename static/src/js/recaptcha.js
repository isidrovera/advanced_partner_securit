/** @odoo-module **/
import { registry } from "@web/core/registry";

// Prevenir múltiples inicializaciones
if (window._turnstileInitialized) {
    console.log("[Turnstile] Ya inicializado, evitando doble carga");
} else {
    // Marcar como inicializado
    window._turnstileInitialized = true;
    
    // IIFE para limpiar captchas duplicados inmediatamente
    (function() {
        // Función para eliminar captchas duplicados
        function cleanupDuplicateCaptchas() {
            const containers = document.querySelectorAll(".cf-turnstile");
            if (containers.length <= 1) return;
            
            console.log("[Turnstile] Encontrados " + containers.length + " captchas, eliminando " + (containers.length - 1) + " duplicados");
            
            // Mantener solo el primer contenedor
            for (let i = 1; i < containers.length; i++) {
                try {
                    containers[i].parentNode.removeChild(containers[i]);
                } catch (e) {
                    console.error("[Turnstile] Error al eliminar captcha:", e);
                }
            }
        }
        
        // Limpiar en diferentes momentos para asegurar que funcione
        // 1. Inmediatamente si el DOM ya está cargado
        if (document.readyState !== "loading") {
            cleanupDuplicateCaptchas();
        }
        
        // 2. Cuando el DOM esté completamente cargado
        document.addEventListener("DOMContentLoaded", cleanupDuplicateCaptchas);
        
        // 3. Después de que la página esté completamente cargada
        window.addEventListener("load", cleanupDuplicateCaptchas);
        
        // 4. Periódicamente durante los primeros segundos después de la carga
        let cleanupAttempts = 0;
        const cleanupInterval = setInterval(function() {
            cleanupDuplicateCaptchas();
            cleanupAttempts++;
            if (cleanupAttempts >= 10) {
                clearInterval(cleanupInterval);
            }
        }, 500);
        
        // 5. Observar cambios en el DOM para eliminar captchas que puedan aparecer dinámicamente
        if (typeof MutationObserver !== 'undefined') {
            const observer = new MutationObserver(function(mutations) {
                let shouldCleanup = false;
                
                for (const mutation of mutations) {
                    if (mutation.type === 'childList') {
                        // Comprobar si se agregaron nodos relacionados con captcha
                        for (const node of mutation.addedNodes) {
                            if (node.nodeType === 1) { // Elemento
                                if (node.classList?.contains('cf-turnstile') || node.querySelector?.('.cf-turnstile')) {
                                    shouldCleanup = true;
                                    break;
                                }
                            }
                        }
                    }
                    
                    if (shouldCleanup) break;
                }
                
                if (shouldCleanup) {
                    cleanupDuplicateCaptchas();
                }
            });
            
            // Configurar el observador para vigilar todo el árbol del DOM
            observer.observe(document.documentElement || document.body, {
                childList: true,
                subtree: true
            });
            
            // Guardar referencia para evitar pérdida de memoria
            window._turnstileObserver = observer;
        }
    })();
}

// Variable global para controlar el estado de renderización
let turnstileRendered = false;

const TurnstileValidator = {
    init: function() {
        console.log("[Turnstile] Iniciando validación...");
        
        // Verificar si el DOM ya está cargado
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", () => {
                this.setup();
            });
        } else {
            // El DOM ya está cargado
            this.setup();
        }
    },
    
    setup: function() {
        // Eliminar cualquier captcha duplicado antes de iniciar
        this.removeDuplicates();
        
        // No inicializar si ya hay un iframe (captcha ya renderizado)
        if (document.querySelector('.cf-turnstile iframe')) {
            console.log("[Turnstile] Ya hay un iframe, saltando inicialización");
            turnstileRendered = true;
            return;
        }
        
        this.loadTurnstileScript();
        this.attachValidator();
    },
    
    removeDuplicates: function() {
        const containers = document.querySelectorAll(".cf-turnstile");
        if (containers.length <= 1) return;
        
        console.log("[Turnstile] Eliminando captchas duplicados...");
        
        // Mantener solo el primer contenedor
        for (let i = 1; i < containers.length; i++) {
            try {
                containers[i].parentNode.removeChild(containers[i]);
            } catch (e) {
                console.error("[Turnstile] Error al eliminar captcha:", e);
            }
        }
    },
    
    loadTurnstileScript: function() {
        // Evitar cargar el script si ya existe o si ya está renderizado
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
    
    waitForTurnstileAPI: function() {
        let attempts = 0;
        const maxAttempts = 20; // 5 segundos máximo
        
        const checkAPI = () => {
            if (typeof window.turnstile !== "undefined") {
                this.renderTurnstile();
            } else if (++attempts < maxAttempts) {
                setTimeout(checkAPI, 250);
            } else {
                console.error("[Turnstile] La API no estuvo disponible después de varios intentos");
            }
        };
        
        checkAPI();
    },
    
    renderTurnstile: function() {
        // No renderizar si ya está renderizado
        if (turnstileRendered) {
            console.log("[Turnstile] Ya está renderizado, saltando");
            return;
        }
        
        // No renderizar si ya hay un iframe (captcha ya renderizado)
        if (document.querySelector('.cf-turnstile iframe')) {
            console.log("[Turnstile] Se detectó un iframe existente, no se renderizará");
            turnstileRendered = true;
            return;
        }
        
        // Eliminar duplicados antes de renderizar
        this.removeDuplicates();
        
        // Obtener el contenedor
        const container = document.querySelector(".cf-turnstile");
        if (!container) {
            console.warn("[Turnstile] No se encontró contenedor para el captcha");
            return;
        }
        
        // Asegurarse de que el contenedor tenga un ID
        if (!container.id) {
            container.id = "cf-turnstile-container";
        }
        
        // Limpiar el contenedor antes de renderizar
        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }
        
        console.log("[Turnstile] Renderizando captcha en contenedor:", container.id);
        
        try {
            // Marcar como renderizado antes de renderizar, para evitar múltiples intentos
            turnstileRendered = true;
            
            // Renderizar el captcha
            window.turnstile.render(container, {
                sitekey: "0x4AAAAAAA-dpmO_dMh_oBeK",
                theme: "light",
                callback: (token) => {
                    console.log("[Turnstile] Token generado correctamente");
                    const responseField = document.getElementById("cf-turnstile-response");
                    if (responseField) {
                        responseField.value = token;
                    } else {
                        // Si no existe el campo, crearlo
                        const hiddenField = document.createElement("input");
                        hiddenField.type = "hidden";
                        hiddenField.id = "cf-turnstile-response";
                        hiddenField.name = "cf-turnstile-response";
                        hiddenField.value = token;
                        container.appendChild(hiddenField);
                    }
                },
                "error-callback": () => {
                    console.error("[Turnstile] Error generando token");
                }
            });
        } catch (error) {
            console.error("[Turnstile] Error al renderizar:", error);
            turnstileRendered = false; // Permitir otro intento
        }
    },
    
    attachValidator: function() {
        const form = document.querySelector("form.oe_signup_form");
        if (!form) {
            console.warn("[Turnstile] Formulario no encontrado");
            return;
        }
        
        // Evitar adjuntar múltiples validadores
        if (form.dataset.turnstileValidatorAttached === "true") {
            return;
        }
        
        form.addEventListener("submit", this.validateTurnstile.bind(this));
        form.dataset.turnstileValidatorAttached = "true";
    },
    
    validateTurnstile: function(ev) {
        const turnstileResponse = document.querySelector('input[name="cf-turnstile-response"]')?.value;
        
        if (!turnstileResponse) {
            ev.preventDefault();
            
            // Mostrar mensaje de error
            const errorContainer = document.createElement("div");
            errorContainer.className = "alert alert-danger mt-2";
            errorContainer.textContent = "Por favor, completa la verificación de seguridad antes de continuar.";
            
            const captchaField = document.querySelector(".field-captcha");
            if (captchaField) {
                // Eliminar cualquier error anterior
                const previousError = captchaField.querySelector(".alert");
                if (previousError) {
                    previousError.remove();
                }
                
                captchaField.appendChild(errorContainer);
            } else {
                alert("Por favor, completa la verificación de seguridad antes de continuar.");
            }
            
            return false;
        }
        
        return true;
    }
};

// Inicializar con retraso para permitir que la limpieza se ejecute primero
setTimeout(() => {
    TurnstileValidator.init();
}, 100);

// Registrar el servicio para Odoo
const turnstileService = {
    dependencies: [],
    start() {
        console.log("[Turnstile] Servicio iniciado");
        return TurnstileValidator;
    },
};

registry.category("services").add("turnstile_validator", turnstileService);

export default TurnstileValidator;