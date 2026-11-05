/**
 * Comportamento assíncrono para o módulo de Registro de Horas (Timesheet).
 * Elimina o recarregamento total da página e atualiza o histórico em tempo real.
 * Atende às diretrizes WCAG 2.1 (Acessibilidade) e disciplina COM120.
 */

document.addEventListener('DOMContentLoaded', () => {
    const timesheetForm = document.querySelector('.timesheet-form');
    if (!timesheetForm) return;

    const submitBtn = timesheetForm.querySelector('button[type="submit"]');
    const entryList = document.querySelector('.entry-list');

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
                showToast(result.data.message || 'Lançamento registrado com sucesso!', 'success');

                // Insere dinamicamente o novo registro na lista de últimos lançamentos
                if (entryList && result.data.entry) {
                    const entry = result.data.entry;
                    const li = document.createElement('li');
                    li.className = 'entry-item-animated';
                    li.innerHTML = `
                        <strong>${entry.user}</strong>
                        <span>${entry.project} · ${entry.task}</span>
                        <span>${entry.date} · ${entry.hours_worked}h</span>
                    `;

                    // Remove mensagem de "Nenhum lançamento encontrado" se existir
                    const emptyItem = entryList.querySelector('li:only-child');
                    if (emptyItem && emptyItem.textContent.includes('Nenhum lançamento')) {
                        emptyItem.remove();
                    }

                    entryList.prepend(li);
                }

                // Limpa campos específicos sem perder a data ou seleção de usuário
                const hoursInput = timesheetForm.querySelector('[name="hours_worked"]');
                const descInput = timesheetForm.querySelector('[name="description"]');
                if (hoursInput) hoursInput.value = '';
                if (descInput) descInput.value = '';

                // Retorna o foco para o campo de horas para agilizar múltiplos lançamentos
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
