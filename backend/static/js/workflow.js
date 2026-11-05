/**
 * Comportamento assíncrono para o workflow de tarefas do consultor.
 * Figura 1 e Figura 6 do relatório - UNIVESP COM120.
 */

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.task-request-completion-form').forEach(form => {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            const taskId = form.dataset.taskId;
            if (!taskId) return;

            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.textContent = 'Enviando...';

            try {
                const result = await apiRequest(`/api/v1/tasks/${taskId}/request-completion/`, {
                    method: 'POST',
                });

                if (result.ok && result.data.success) {
                    showToast(result.data.message || 'Solicitação enviada com sucesso!', 'success');

                    // Atualiza dinamicamente o card da tarefa na tela
                    const card = form.closest('.task-workflow-card');
                    if (card) {
                        const statusBadge = card.querySelector('.task-status');
                        if (statusBadge) {
                            statusBadge.className = 'task-status task-status-review';
                            statusBadge.textContent = 'Em validação';
                        }

                        // Substitui o formulário pela mensagem de status
                        const notice = document.createElement('small');
                        notice.className = 'muted-text';
                        notice.textContent = 'Sua solicitação foi enviada. Agora a gestão precisa validar a conclusão.';
                        form.replaceWith(notice);
                    }
                } else {
                    showToast(result.data.message || 'Erro ao solicitar validação da tarefa.', 'error');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }
            } catch (err) {
                console.error('Erro na solicitação de validação:', err);
                showToast('Falha na comunicação com o servidor.', 'error');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    });
});
