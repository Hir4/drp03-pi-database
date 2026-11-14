/**
 * ui.js - Comportamentos de interface compartilhados por todas as telas.
 *
 * 1. Menu recolhível no celular (botão "Menu" com aria-expanded).
 * 2. Confirmação acessível antes de ações destrutivas: qualquer <form> com
 *    data-confirm="Mensagem" abre o <dialog id="confirm-dialog"> antes de enviar.
 * 3. Painéis (<dialog>) de criar/editar: botões com data-dialog-open="id" abrem
 *    o painel; data-fill='{"campo": "valor"}' preenche o formulário de edição
 *    com os dados da linha clicada. O foco volta para o botão ao fechar.
 * 4. Links para "#tarefas-projeto-X" abrem o <details> correspondente.
 * 5. Tema claro/escuro: botão [data-theme-toggle] grava a escolha no navegador
 *    (localStorage "fcn-theme"); sem escolha, segue o tema do sistema. O tema é
 *    aplicado ainda no <head> (base.html) para a tela não "piscar" em branco.
 */

(function () {
    "use strict";

    const MOBILE_QUERY = window.matchMedia("(max-width: 960px)");

    /* ---------- 1. Menu no celular ---------- */
    function initNavToggle() {
        const toggle = document.querySelector(".nav-toggle");
        const sidebar = document.querySelector(".sidebar");
        if (!toggle || !sidebar) return;

        const setOpen = (open) => {
            sidebar.classList.toggle("is-open", open);
            toggle.setAttribute("aria-expanded", String(open));
            toggle.querySelector(".nav-toggle-label").textContent = open ? "Fechar" : "Menu";
        };

        toggle.addEventListener("click", () => setOpen(!sidebar.classList.contains("is-open")));
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && sidebar.classList.contains("is-open")) {
                setOpen(false);
                toggle.focus();
            }
        });
        MOBILE_QUERY.addEventListener("change", () => setOpen(false));
    }

    /* ---------- 2. Confirmação de ações destrutivas ---------- */
    function initConfirmForms() {
        const dialog = document.getElementById("confirm-dialog");
        if (!dialog) return;
        const text = dialog.querySelector("#confirm-dialog-text");
        const title = dialog.querySelector("#confirm-dialog-title");
        const accept = dialog.querySelector("[data-confirm-accept]");
        const cancel = dialog.querySelector("[data-confirm-cancel]");
        let pendingForm = null;
        let opener = null;

        document.addEventListener("submit", (event) => {
            const form = event.target;
            if (!(form instanceof HTMLFormElement) || !form.dataset.confirm) return;
            if (form.dataset.confirmed === "1") {
                delete form.dataset.confirmed;
                return;
            }
            event.preventDefault();

            if (typeof dialog.showModal !== "function") {
                // Navegadores sem <dialog>: usa a confirmação nativa.
                if (window.confirm(form.dataset.confirm)) {
                    form.dataset.confirmed = "1";
                    form.requestSubmit();
                }
                return;
            }

            pendingForm = form;
            opener = event.submitter || document.activeElement;
            title.textContent = form.dataset.confirmTitle || "Confirmar ação";
            text.textContent = form.dataset.confirm;
            accept.textContent = form.dataset.confirmAction || "Confirmar";
            dialog.showModal();
            cancel.focus();
        });

        accept.addEventListener("click", () => {
            dialog.close();
            if (pendingForm) {
                pendingForm.dataset.confirmed = "1";
                pendingForm.requestSubmit();
            }
        });
        cancel.addEventListener("click", () => dialog.close());
        dialog.addEventListener("close", () => {
            pendingForm = null;
            if (opener && typeof opener.focus === "function") opener.focus();
        });
    }

    /* ---------- 3. Painéis de criar/editar ---------- */
    function fillForm(dialog, values) {
        Object.entries(values).forEach(([name, value]) => {
            const field = dialog.querySelector(`[name="${name}"]`);
            if (field) field.value = value ?? "";
        });
    }

    function initDialogs() {
        let opener = null;

        document.addEventListener("click", (event) => {
            const openButton = event.target.closest("[data-dialog-open]");
            if (openButton) {
                const dialog = document.getElementById(openButton.dataset.dialogOpen);
                if (!dialog || typeof dialog.showModal !== "function") return;
                event.preventDefault();
                opener = openButton;
                if (openButton.dataset.fill) {
                    fillForm(dialog, JSON.parse(openButton.dataset.fill));
                }
                const subtitle = dialog.querySelector("[data-dialog-subtitle]");
                if (subtitle && openButton.dataset.subtitle) {
                    subtitle.textContent = openButton.dataset.subtitle;
                }
                dialog.showModal();
                const firstField = dialog.querySelector("input:not([type=hidden]), select, textarea");
                if (firstField) firstField.focus();
                return;
            }

            const closeButton = event.target.closest("[data-dialog-close]");
            if (closeButton) {
                const dialog = closeButton.closest("dialog");
                if (dialog) dialog.close();
            }
        });

        document.querySelectorAll("dialog.app-dialog").forEach((dialog) => {
            dialog.addEventListener("close", () => {
                if (opener && document.contains(opener)) opener.focus();
                opener = null;
            });
            // Clique fora do conteúdo fecha o painel.
            dialog.addEventListener("click", (event) => {
                if (event.target === dialog) dialog.close();
            });
        });

        // Formulário que voltou do servidor com erro: reabre o painel certo.
        const toOpen = document.body.dataset.openDialog;
        if (toOpen) {
            const dialog = document.getElementById(toOpen);
            if (dialog && typeof dialog.showModal === "function") dialog.showModal();
        }
    }

    /* ---------- 4. Âncoras para <details> ---------- */
    function openDetailsFromHash() {
        if (!location.hash) return;
        const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
        if (target && target.tagName === "DETAILS") {
            target.open = true;
            target.scrollIntoView({ block: "start" });
            const summary = target.querySelector("summary");
            if (summary) summary.focus();
        }
    }

    /* ---------- 5. Tema claro/escuro ---------- */
    const THEME_KEY = "fcn-theme";

    function storedTheme() {
        try {
            return window.localStorage.getItem(THEME_KEY);
        } catch (error) {
            return null;
        }
    }

    function applyTheme(theme, persist) {
        document.documentElement.dataset.theme = theme;
        if (persist) {
            try {
                window.localStorage.setItem(THEME_KEY, theme);
            } catch (error) {
                /* navegação privada: o tema vale só para esta página */
            }
        }
        syncThemeButtons();
        document.dispatchEvent(new CustomEvent("fcn:themechange", { detail: { theme } }));
    }

    function syncThemeButtons() {
        const dark = document.documentElement.dataset.theme === "dark";
        document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
            button.setAttribute("aria-label", dark ? "Ativar tema claro" : "Ativar tema escuro");
            button.querySelector(".theme-toggle-icon").textContent = dark ? "☀" : "☾";
            button.querySelector(".theme-toggle-label").textContent = dark ? "Tema claro" : "Tema escuro";
        });
    }

    function initThemeToggle() {
        syncThemeButtons();
        document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
            button.addEventListener("click", () => {
                const dark = document.documentElement.dataset.theme === "dark";
                applyTheme(dark ? "light" : "dark", true);
            });
        });
        // Sem escolha salva, acompanha a troca de tema do sistema operacional.
        const systemDark = window.matchMedia("(prefers-color-scheme: dark)");
        systemDark.addEventListener("change", (event) => {
            if (!storedTheme()) applyTheme(event.matches ? "dark" : "light", false);
        });
    }

    function init() {
        initThemeToggle();
        initNavToggle();
        initConfirmForms();
        initDialogs();
        openDetailsFromHash();
        window.addEventListener("hashchange", openDetailsFromHash);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
