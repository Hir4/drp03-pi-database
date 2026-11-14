/**
 * Comportamento assíncrono para o módulo de Registro de Horas (Timesheet).
 * Elimina o recarregamento total da página, atualiza o histórico e os totais
 * de hoje/semana em tempo real. Atende às diretrizes WCAG 2.1 (Acessibilidade).
 */

document.addEventListener('DOMContentLoaded', () => {
    const timesheetForm = document.querySelector('.timesheet-form');
    if (!timesheetForm) return;

    const submitBtn = timesheetForm.querySelector('button[type="submit"]');
    const entryList = document.getElementById('timesheet-entry-list');

    // Remove mensagens de erro antigas da interface
    function clearFormErrors() {
        timesheetForm.querySelectorAll('.field-error-msg').forEach(el => el.remove());
        timesheetForm.querySelectorAll('[aria-invalid="true"]').forEach(el => {
            el.removeAttribute('aria-invalid');
            el.removeAttribute('aria-describedby');
        });
    }

    // Exibe erros específicos de campos com atributos de acessibilidade
    function displayFormErrors(errors) {
        let firstInvalidField = null;

        for (const [fieldName, errorMessages] of Object.entries(errors)) {
            const field = timesheetForm.querySelector(`[name="${fieldName}"]`);
            if (field) {
                const parent = field.closest('.form-field') || field.parentElement;
                field.setAttribute('aria-invalid', 'true');

                const errorId = `error-${fieldName}`;
                field.setAttribute('aria-describedby', errorId);

                const errorEl = document.createElement('small');
                errorEl.id = errorId;
                errorEl.className = 'error field-error-msg';
                errorEl.setAttribute('role', 'alert');
                errorEl.textContent = Array.isArray(errorMessages) ? errorMessages.join(', ') : errorMessages;

                parent.appendChild(errorEl);

                if (!firstInvalidField) {
                    firstInvalidField = field;
                }
            }
        }

        // Foca no primeiro campo com erro para apoiar navegação por teclado
        if (firstInvalidField) {
            firstInvalidField.focus();
        }
    }

    // Cria o item do histórico com textContent (evita injeção de HTML)
    function buildEntryItem(entry) {
        const li = document.createElement('li');
        li.className = 'entry-item entry-item-animated';

        const top = document.createElement('div');
        top.className = 'entry-item-top';
        const date = document.createElement('strong');
        date.textContent = entry.date;
        const hours = document.createElement('span');
        hours.className = 'entry-hours';
        hours.textContent = `${String(entry.hours_worked).replace(/(,\d)0$/, "$1")}h`;
        top.append(date, hours);
        li.appendChild(top);

        if (entryList.dataset.showUser === '1') {
            const user = document.createElement('span');
            user.className = 'entry-user';
            user.textContent = entry.user;
            li.appendChild(user);
        }

        const task = document.createElement('span');
        task.textContent = `${entry.task} · ${entry.project}`;
        li.appendChild(task);

        if (!entry.is_billable) {
            const tag = document.createElement('small');
            tag.className = 'tag-muted';
            tag.textContent = 'Não faturável';
            li.appendChild(tag);
        }
        return li;
    }

    function updateTotals(totals) {
        if (!totals) return;
        const today = document.getElementById('summary-today-hours');
        const week = document.getElementById('summary-week-hours');
        const bar = document.getElementById('summary-week-bar');
        if (today) today.textContent = `${totals.today_hours}h`;
        if (week) week.textContent = `${totals.week_hours}h`;
        if (bar) {
            const value = Math.round(totals.week_progress);
            bar.setAttribute('aria-valuenow', String(value));
            const fill = bar.querySelector('span');
            if (fill) fill.style.width = `${value}%`;
        }
    }

    timesheetForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        clearFormErrors();

        // Feedback de carregamento no botão
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.setAttribute('aria-busy', 'true');
        submitBtn.textContent = 'Salvando lançamento...';

        const formData = new FormData(timesheetForm);

        try {
            const result = await apiRequest('/api/v1/timesheet/', {
                method: 'POST',
                body: formData,
            });

            if (result.ok && result.data.success) {
                const totals = result.data.totals;
                const message = totals
                    ? `${result.data.message} Hoje: ${totals.today_hours}h · Semana: ${totals.week_hours}h de ${totals.week_target}h.`
                    : (result.data.message || 'Lançamento registrado com sucesso!');
                showToast(message, 'success');
                updateTotals(totals);

                // Insere dinamicamente o novo registro na lista de últimos lançamentos
                if (entryList && result.data.entry) {
                    const emptyItem = entryList.querySelector('.empty-entry');
                    if (emptyItem) emptyItem.remove();
                    entryList.prepend(buildEntryItem(result.data.entry));
                }

                // Limpa horas e descrição, mantendo tarefa e data para lançamentos em sequência
                const hoursInput = timesheetForm.querySelector('[name="hours_worked"]');
                const descInput = timesheetForm.querySelector('[name="description"]');
                if (hoursInput) hoursInput.value = '';
                if (descInput) descInput.value = '';
                if (hoursInput) hoursInput.focus();

            } else {
                const errorMsg = result.data.message || 'Erro ao salvar lançamento. Verifique os campos.';
                showToast(errorMsg, 'error');

                if (result.data.errors) {
                    displayFormErrors(result.data.errors);
                }
            }
        } catch (error) {
            console.error('Falha na comunicação assíncrona:', error);
            showToast('Falha na conexão com o servidor. Tente novamente.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.removeAttribute('aria-busy');
            submitBtn.innerHTML = originalBtnText;
        }
    });
});
