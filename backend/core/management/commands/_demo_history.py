"""Histórico ampliado de demonstração usado pelo comando ``seed_demo_data``.

Gera, de forma determinística, lançamentos de horas de janeiro até
``HISTORY_END`` para alimentar o dashboard e a tela de Análises com séries
temporais, carga da equipe, estouros de estimativa e projetos em risco.

Regras de geração:
- Apenas dias úteis, sem feriados nacionais de 2026.
- Cada pessoa lança no máximo ``DAILY_CAP`` horas por dia, somando todas as
  tarefas (inclusive os lançamentos fixos do seed).
- A aleatoriedade usa sementes fixas por tarefa, então rodar o seed de novo
  produz exatamente os mesmos lançamentos (idempotente).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

HISTORY_END = date(2026, 11, 13)
DAILY_CAP = Decimal("8.0")
HALF_HOUR = Decimal("0.5")
MIN_CHUNK = Decimal("1.0")

HOLIDAYS_2026 = {
    date(2026, 1, 1),
    date(2026, 2, 16),
    date(2026, 2, 17),
    date(2026, 4, 3),
    date(2026, 4, 21),
    date(2026, 5, 1),
    date(2026, 6, 4),
    date(2026, 9, 7),
    date(2026, 10, 12),
    date(2026, 11, 2),
}


@dataclass(frozen=True)
class ExtraTask:
    key: str
    project: str
    name: str
    estimated_hours: str
    assignee: str | None


@dataclass(frozen=True)
class WorkPlan:
    task: str
    user: str
    start: date
    end: date
    hours: int
    billable_ratio: float
    descriptions: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowState:
    """Estado do fluxo de validação. ``validated_at`` vazio = aguardando aprovação."""

    task: str
    requested_by: str
    requested_at: datetime
    validated_by: str | None = None
    validated_at: datetime | None = None


EXTRA_TASKS: tuple[ExtraTask, ...] = (
    # Indústria Atlas · Sustentação ERP
    ExtraTask("task_2b", "sustentacao_erp", "Correções evolutivas do módulo de compras", "80.00", "bruno"),
    ExtraTask("task_2c", "sustentacao_erp", "Rotina de fechamento contábil assistido", "160.00", "pedro"),
    ExtraTask("task_2d", "sustentacao_erp", "Atualização de versão do ERP", "90.00", "thiago"),
    # Indústria Atlas · Modernização de Dados
    ExtraTask("task_3e", "modernizacao_dados", "Catálogo de dados e governança", "60.00", "pedro"),
    ExtraTask("task_3f", "modernizacao_dados", "Painel executivo de margem por unidade", "40.00", "larissa"),
    # Grupo Horizonte · Portal do Cliente
    ExtraTask("task_4c", "portal_cliente", "Área de autoatendimento e segunda via de boletos", "140.00", "aline"),
    ExtraTask("task_4d", "portal_cliente", "Homologação final e go-live", "40.00", "renata"),
    ExtraTask("task_4e", "portal_cliente", "Ajustes pós go-live", "24.00", "bruno"),
    # Logística Prisma · Observabilidade Operacional
    ExtraTask("task_5c", "observabilidade", "Alertas e SLOs por serviço crítico", "120.00", "caio"),
    ExtraTask("task_5d", "observabilidade", "Dashboards de capacidade da operação", "80.00", "thiago"),
    # Hospital Aurora · App do Paciente
    ExtraTask("task_6c", "app_pacientes", "Notificações push e lembretes de consulta", "80.00", "aline"),
    ExtraTask("task_6d", "app_pacientes", "Testes de acessibilidade do aplicativo", "40.00", "renata"),
    ExtraTask("task_6e", "app_pacientes", "Prontuário resumido no aplicativo", "120.00", None),
    # Hospital Aurora · Analytics de Suprimentos
    ExtraTask("task_7b", "analytics_suprimentos", "Previsão de demanda por unidade", "90.00", "larissa"),
    ExtraTask("task_7c", "analytics_suprimentos", "Integração com ERP de compras", "50.00", "pedro"),
    # Varejo Nexus · Portal B2B
    ExtraTask("task_8c", "ecommerce_b2b", "Checkout corporativo e faturamento", "120.00", "bruno"),
    ExtraTask("task_8d", "ecommerce_b2b", "Integração com marketplace parceiro", "70.00", "aline"),
    ExtraTask("task_8e", "ecommerce_b2b", "Testes de carga do portal", "30.00", "renata"),
    # Cooperativa Vale Verde · Migração para Nuvem
    ExtraTask("task_10", "migracao_nuvem", "Assessment da infraestrutura atual", "40.00", "thiago"),
    ExtraTask("task_10b", "migracao_nuvem", "Landing zone, redes e identidades", "80.00", "caio"),
    ExtraTask("task_10c", "migracao_nuvem", "Plano de migração das aplicações", "50.00", "thiago"),
    ExtraTask("task_10d", "migracao_nuvem", "Migração do banco de dados transacional", "70.00", None),
)


def _d(month: int, day: int) -> date:
    return date(2026, month, day)


def _dt(month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, month, day, hour, minute)


WORK_PLANS: tuple[WorkPlan, ...] = (
    # --- Sustentação ERP (saudável) ---
    WorkPlan("task_2", "julia", _d(1, 5), _d(3, 31), 44, 0.9, (
        "Tratamento de chamados de integração fiscal",
        "Análise de rejeições recorrentes de notas fiscais",
        "Ajuste de parâmetros fiscais após mudança de alíquota",
    )),
    WorkPlan("task_1", "pedro", _d(1, 5), _d(3, 27), 60, 0.85, (
        "Atendimento de chamados de sustentação do ERP",
        "Registro e categorização de incidentes recorrentes",
        "Apoio ao usuário-chave na rotina de faturamento",
    )),
    WorkPlan("task_1", "marina", _d(1, 12), _d(3, 27), 24, 0.9, (
        "Triagem semanal de incidentes com o suporte do cliente",
        "Classificação de criticidade e plano de ação",
        "Reunião de acompanhamento com o key-user do ERP",
    )),
    WorkPlan("task_2", "julia", _d(4, 13), _d(6, 19), 56, 0.9, (
        "Ajuste de regras de ICMS-ST na integração fiscal",
        "Validação de notas fiscais com a contabilidade",
        "Correção de rejeições da SEFAZ em homologação",
    )),
    WorkPlan("task_2b", "bruno", _d(6, 1), _d(9, 18), 96, 0.9, (
        "Correção no fluxo de aprovação de pedidos de compra",
        "Melhoria na tela de cotação de fornecedores",
        "Ajuste de relatório de compras pendentes",
    )),
    WorkPlan("task_2c", "pedro", _d(5, 4), _d(11, 13), 150, 0.85, (
        "Conferência de lançamentos do fechamento mensal",
        "Conciliação bancária assistida com o financeiro",
        "Ajuste de rotina de provisões do fechamento",
    )),
    WorkPlan("task_2d", "thiago", _d(9, 14), _d(11, 13), 72, 0.9, (
        "Levantamento de customizações impactadas pela nova versão",
        "Atualização do ambiente de homologação do ERP",
        "Testes de regressão após atualização de versão",
    )),
    # --- Modernização de Dados (saudável) ---
    WorkPlan("task_3", "julia", _d(2, 2), _d(7, 31), 90, 0.85, (
        "Evolução da ingestão incremental de vendas",
        "Tratamento de falhas e reprocessamento do pipeline",
        "Monitoramento de qualidade de dados na carga diária",
    )),
    WorkPlan("task_3b", "larissa", _d(5, 11), _d(8, 28), 42, 0.9, (
        "Modelagem de métricas de margem e receita",
        "Revisão da camada semântica com controladoria",
        "Documentação de regras de negócio dos indicadores",
    )),
    WorkPlan("task_3e", "pedro", _d(8, 3), _d(11, 13), 58, 0.8, (
        "Cadastro de tabelas e responsáveis no catálogo de dados",
        "Definição de políticas de acesso por domínio",
        "Revisão de glossário de negócio com as áreas",
    )),
    WorkPlan("task_3f", "larissa", _d(9, 8), _d(11, 6), 34, 0.9, (
        "Construção do painel de margem por unidade de negócio",
        "Ajuste de filtros e drill-down do painel executivo",
        "Validação dos números com a controladoria",
    )),
    # --- Portal do Cliente (quase concluído, saudável) ---
    WorkPlan("task_4", "bruno", _d(2, 18), _d(6, 26), 128, 0.95, (
        "Implementação de login com MFA e recuperação de senha",
        "Perfis de acesso por empresa e por usuário",
        "Integração do portal com o diretório do cliente",
    )),
    WorkPlan("task_4", "marina", _d(2, 18), _d(8, 28), 30, 1.0, (
        "Reunião de status semanal com o Grupo Horizonte",
        "Revisão de escopo e priorização do backlog",
    )),
    WorkPlan("task_4b", "renata", _d(5, 11), _d(7, 3), 30, 0.9, (
        "Execução de casos de teste de autenticação",
        "Registro e reteste de defeitos de autorização",
        "Teste da jornada crítica de primeiro acesso",
    )),
    WorkPlan("task_4c", "aline", _d(3, 16), _d(8, 21), 168, 0.95, (
        "Protótipo navegável da área de autoatendimento",
        "Implementação da emissão de segunda via de boletos",
        "Ajustes de usabilidade a partir de testes com usuários",
    )),
    WorkPlan("task_4d", "renata", _d(8, 3), _d(8, 28), 38, 1.0, (
        "Homologação com usuários-chave do cliente",
        "Checklist de go-live e plano de rollback",
        "Acompanhamento da virada para produção",
    )),
    WorkPlan("task_4e", "bruno", _d(9, 1), _d(9, 30), 30, 0.6, (
        "Correção de defeitos reportados após o go-live",
        "Ajuste de performance na listagem de faturas",
    )),
    # --- Observabilidade Operacional (atenção) ---
    WorkPlan("task_5", "caio", _d(3, 2), _d(4, 24), 70, 0.9, (
        "Configuração dos coletores de logs nos servidores",
        "Padronização do formato de logs das aplicações",
        "Criação de índices e retenção de logs",
    )),
    WorkPlan("task_5b", "caio", _d(5, 4), _d(7, 17), 52, 0.85, (
        "Revisão de permissões do cluster de monitoramento",
        "Rotação de credenciais e segredos",
        "Configuração de trilha de auditoria de acessos",
    )),
    WorkPlan("task_5c", "caio", _d(7, 20), _d(11, 13), 140, 0.85, (
        "Definição de SLOs com os donos dos serviços",
        "Configuração de alertas por severidade",
        "Ajuste de ruído e escalonamento de alertas",
    )),
    WorkPlan("task_5c", "rodrigo", _d(7, 20), _d(11, 13), 20, 0.3, (
        "Revisão interna de SLOs e riscos operacionais",
        "Alinhamento de prioridades com a operação do cliente",
    )),
    WorkPlan("task_5d", "thiago", _d(6, 1), _d(11, 13), 110, 0.8, (
        "Painel de capacidade de CPU, memória e disco",
        "Projeção de crescimento de infraestrutura",
        "Revisão dos painéis com o time de operação",
    )),
    # --- App do Paciente (em risco: estouro de horas e pouco avanço) ---
    WorkPlan("task_6", "aline", _d(1, 26), _d(3, 13), 50, 0.9, (
        "Entrevistas com pacientes e equipe de recepção",
        "Mapa de jornada do paciente",
        "Protótipo de baixa fidelidade das telas principais",
    )),
    WorkPlan("task_6", "bruno", _d(2, 9), _d(5, 29), 92, 0.9, (
        "Desenvolvimento das telas de agendamento",
        "Integração do app com a API de autenticação",
        "Correções do protótipo após validação clínica",
    )),
    WorkPlan("task_6b", "julia", _d(6, 1), _d(11, 13), 200, 0.8, (
        "Integração com a agenda legada do hospital",
        "Tratamento de conflitos de horário entre sistemas",
        "Retrabalho após mudança na API da agenda",
    )),
    WorkPlan("task_6c", "aline", _d(8, 24), _d(11, 13), 118, 0.85, (
        "Fluxo de notificações e preferências do paciente",
        "Lembretes automáticos de consulta e exames",
        "Ajustes de layout das notificações",
    )),
    WorkPlan("task_6d", "renata", _d(10, 1), _d(11, 13), 36, 0.9, (
        "Teste com leitor de tela no aplicativo",
        "Verificação de contraste e tamanho de fonte",
        "Registro de defeitos de acessibilidade",
    )),
    WorkPlan("task_6", "marina", _d(3, 2), _d(11, 13), 26, 0.7, (
        "Reunião de status com a diretoria do Hospital Aurora",
        "Replanejamento do cronograma do app",
    )),
    # --- Analytics de Suprimentos (saudável) ---
    WorkPlan("task_7", "larissa", _d(4, 13), _d(10, 30), 52, 0.9, (
        "Evolução dos indicadores de ruptura por unidade",
        "Painel de giro de estoque por categoria",
        "Validação dos dashboards com a área de suprimentos",
    )),
    WorkPlan("task_7b", "larissa", _d(6, 1), _d(9, 25), 88, 0.9, (
        "Preparação de séries históricas de consumo",
        "Modelo de previsão de demanda por unidade",
        "Avaliação de erro da previsão com suprimentos",
    )),
    WorkPlan("task_7c", "pedro", _d(4, 20), _d(7, 31), 56, 0.85, (
        "Mapeamento das tabelas de compras do ERP",
        "Carga diária de pedidos e recebimentos",
        "Conferência de divergências com o ERP",
    )),
    # --- Portal B2B (saudável) ---
    WorkPlan("task_8", "bruno", _d(4, 13), _d(7, 31), 84, 0.95, (
        "Cadastro de tabelas de preço por perfil de cliente",
        "Regras de desconto por volume",
        "Ajustes no catálogo após feedback comercial",
    )),
    WorkPlan("task_8c", "bruno", _d(8, 3), _d(10, 23), 118, 0.95, (
        "Fluxo de checkout com aprovação do comprador",
        "Integração com faturamento e emissão de NF",
        "Correções do checkout em homologação",
    )),
    WorkPlan("task_8d", "aline", _d(8, 24), _d(11, 13), 62, 0.9, (
        "Mapeamento da API do marketplace parceiro",
        "Sincronização de catálogo e estoque",
        "Tratamento de pedidos vindos do marketplace",
    )),
    WorkPlan("task_8e", "renata", _d(10, 5), _d(10, 30), 28, 1.0, (
        "Preparação de roteiros de teste de carga",
        "Execução de testes de carga no checkout",
        "Relatório de gargalos de performance",
    )),
    WorkPlan("task_8c", "rodrigo", _d(4, 13), _d(10, 30), 18, 0.8, (
        "Comitê quinzenal com o Varejo Nexus",
        "Revisão de riscos e dependências do Portal B2B",
    )),
    # --- Migração para Nuvem (início do projeto) ---
    WorkPlan("task_10", "thiago", _d(9, 1), _d(9, 25), 42, 1.0, (
        "Inventário de servidores e aplicações",
        "Entrevistas com o time de infraestrutura do cliente",
        "Relatório de prontidão para nuvem",
    )),
    WorkPlan("task_10b", "caio", _d(9, 28), _d(11, 13), 62, 0.9, (
        "Desenho da landing zone e contas da organização",
        "Configuração de VPCs, sub-redes e VPN",
        "Políticas de identidade e acesso",
    )),
    WorkPlan("task_10c", "thiago", _d(10, 5), _d(11, 13), 36, 0.9, (
        "Classificação das aplicações por estratégia de migração",
        "Sequenciamento das ondas de migração",
    )),
)


WORKFLOW_STATES: tuple[WorkflowState, ...] = (
    # Concluídas e aprovadas pela gestão
    WorkflowState("task_1", "marina", _dt(4, 14, 17, 40), "marina", _dt(4, 16, 9, 10)),
    WorkflowState("task_5", "caio", _dt(4, 28, 11, 5), "rodrigo", _dt(4, 29, 15, 30)),
    WorkflowState("task_6", "bruno", _dt(5, 29, 17, 20), "marina", _dt(6, 5, 10, 0)),
    WorkflowState("task_2", "julia", _dt(6, 19, 18, 0), "marina", _dt(6, 23, 9, 45)),
    WorkflowState("task_4", "bruno", _dt(6, 26, 16, 30), "marina", _dt(6, 29, 11, 15)),
    WorkflowState("task_4b", "renata", _dt(7, 3, 17, 10), "marina", _dt(7, 8, 14, 0)),
    WorkflowState("task_5b", "caio", _dt(7, 17, 15, 0), "rodrigo", _dt(7, 24, 10, 30)),
    WorkflowState("task_3", "julia", _dt(7, 31, 18, 15), "marina", _dt(8, 6, 9, 0)),
    WorkflowState("task_7c", "pedro", _dt(7, 31, 16, 45), "marina", _dt(8, 4, 11, 20)),
    WorkflowState("task_8", "bruno", _dt(8, 3, 9, 30), "rodrigo", _dt(8, 5, 16, 0)),
    WorkflowState("task_4c", "aline", _dt(8, 21, 17, 0), "marina", _dt(8, 26, 10, 10)),
    WorkflowState("task_3b", "larissa", _dt(8, 28, 15, 40), "marina", _dt(8, 31, 9, 30)),
    WorkflowState("task_4d", "renata", _dt(8, 28, 18, 20), "marina", _dt(9, 2, 14, 45)),
    WorkflowState("task_2b", "bruno", _dt(9, 18, 17, 0), "marina", _dt(9, 21, 9, 50)),
    WorkflowState("task_10", "thiago", _dt(9, 25, 16, 0), "rodrigo", _dt(9, 28, 10, 0)),
    WorkflowState("task_7b", "larissa", _dt(9, 25, 17, 30), "marina", _dt(9, 29, 15, 15)),
    WorkflowState("task_8c", "bruno", _dt(10, 23, 18, 0), "rodrigo", _dt(10, 27, 11, 40)),
    # Aguardando aprovação da gestão (fila de validação)
    WorkflowState("task_4e", "bruno", _dt(10, 1, 9, 15)),
    WorkflowState("task_7", "larissa", _dt(10, 30, 17, 20)),
    WorkflowState("task_8e", "renata", _dt(11, 3, 16, 50)),
    WorkflowState("task_3f", "larissa", _dt(11, 6, 18, 5)),
)


def _workdays(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= min(end, HISTORY_END):
        if current.weekday() < 5 and current not in HOLIDAYS_2026:
            days.append(current)
        current += timedelta(days=1)
    return days


def _round_half(value: Decimal) -> Decimal:
    return (value / HALF_HOUR).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * HALF_HOUR


def _split_hours(total: int, slots: int, rng: random.Random) -> list[Decimal]:
    """Divide o total em blocos de 1h a 8h, arredondados em meia hora, somando o total."""
    weights = [rng.uniform(2.5, 7.0) for _ in range(slots)]
    scale = Decimal(total) / Decimal(str(sum(weights)))
    chunks = [max(MIN_CHUNK, min(DAILY_CAP, _round_half(Decimal(str(weight)) * scale))) for weight in weights]
    difference = Decimal(total) - sum(chunks)
    index = 0
    while difference != 0 and index < slots * 20:
        position = index % slots
        step = HALF_HOUR if difference > 0 else -HALF_HOUR
        candidate = chunks[position] + step
        if MIN_CHUNK <= candidate <= DAILY_CAP:
            chunks[position] = candidate
            difference -= step
        index += 1
    return chunks


def build_generated_entries(
    fixed_entries: list[tuple[str, str, date, str, bool, str]],
) -> list[tuple[str, str, date, Decimal, bool, str]]:
    """Distribui as horas de ``WORK_PLANS`` nos dias úteis respeitando o limite diário por pessoa."""
    load: dict[tuple[str, date], Decimal] = {}
    taken: set[tuple[str, str, date]] = set()
    for username, task_key, entry_date, hours, _billable, _description in fixed_entries:
        load[(username, entry_date)] = load.get((username, entry_date), Decimal("0")) + Decimal(hours)
        taken.add((username, task_key, entry_date))

    generated: list[tuple[str, str, date, Decimal, bool, str]] = []
    for plan in WORK_PLANS:
        days = _workdays(plan.start, plan.end)
        if not days:
            continue
        rng = random.Random(f"{plan.task}:{plan.user}:{plan.start.isoformat()}")
        slots = max(1, min(len(days), round(plan.hours / 4.5)))
        chunks = _split_hours(plan.hours, slots, rng)
        step = len(days) / slots
        for index, chunk in enumerate(chunks):
            day_index = min(len(days) - 1, int(index * step + rng.random() * step))
            remaining = chunk
            billable = rng.random() < plan.billable_ratio
            description = plan.descriptions[index % len(plan.descriptions)]
            while remaining >= MIN_CHUNK and day_index < len(days):
                day = days[day_index]
                key = (plan.user, plan.task, day)
                available = DAILY_CAP - load.get((plan.user, day), Decimal("0"))
                if key not in taken and available >= MIN_CHUNK:
                    hours = min(remaining, available)
                    generated.append((plan.user, plan.task, day, hours, billable, description))
                    load[(plan.user, day)] = load.get((plan.user, day), Decimal("0")) + hours
                    taken.add(key)
                    remaining -= hours
                day_index += 1
    return generated
