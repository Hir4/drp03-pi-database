/**
 * Utilitários de comunicação assíncrona com o Backend Django e acessibilidade.
 * Projeto Integrador II - UNIVESP
 */

// Recupera o token CSRF dos cookies do navegador
function getCsrfToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    // Fallback: busca pelo input hidden do csrf_token no DOM
    if (!cookieValue) {
        const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (csrfInput) {
            cookieValue = csrfInput.value;
        }
    }
    return cookieValue;
}

// Anuncia dinamicamente mensagens para leitores de tela via ARIA Live Region
function announceToScreenReader(message) {
    let announcer = document.getElementById('live-announcer');
    if (!announcer) {
        announcer = document.createElement('div');
        announcer.id = 'live-announcer';
        announcer.className = 'sr-only';
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        document.body.appendChild(announcer);
    }
    // Limpa e reinsere para forçar a leitura imediata
    announcer.textContent = '';
    setTimeout(() => {
        announcer.textContent = message;
    }, 50);
}

// Exibe notificações visuais acessíveis (Toasts) sem recarregar a tela
function showToast(message, type = 'success') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        container.setAttribute('role', 'region');
        container.setAttribute('aria-label', 'Notificações do sistema');
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');

    const icon = type === 'success' ? '✓' : '⚠';
    toast.innerHTML = `
        <span class="toast-icon" aria-hidden="true">${icon}</span>
        <span class="toast-text">${message}</span>
        <button type="button" class="toast-close" aria-label="Fechar notificação">×</button>
    `;

    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 250);
    });

    container.appendChild(toast);
    announceToScreenReader(message);

    // Auto-remove após 4.5 segundos
    setTimeout(() => {
        if (toast.isConnected) {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 250);
        }
    }, 4500);
}

// Wrapper assíncrono para chamadas à API via Fetch
async function apiRequest(url, options = {}) {
    const defaultHeaders = {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
    };

    if (!(options.body instanceof FormData)) {
        defaultHeaders['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, {
        ...options,
        headers: {
            ...defaultHeaders,
            ...options.headers,
        },
    });

    const data = await response.json().catch(() => ({
        success: false,
        message: 'Resposta inesperada do servidor.',
    }));

    return {
        ok: response.ok,
        status: response.status,
        data,
    };
}
