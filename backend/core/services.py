from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce

from .models import Contract, Project, Task, Timesheet, User, UserRole

ZERO = Decimal("0.00")
PERCENT_QUANTIZER = Decimal("0.01")
HOURS_FIELD = DecimalField(max_digits=12, decimal_places=2)
COST_FIELD = DecimalField(max_digits=14, decimal_places=2)


def _apply_management_filters(queryset, filters: dict[str, str] | None):
    if not filters:
        return queryset

    client = filters.get("client")
    manager = filters.get("manager")
    consultant = filters.get("consultant")
    include_archived = filters.get("include_archived") == "1"

    if hasattr(queryset.model, "is_archived") and not include_archived:
        queryset = queryset.filter(is_archived=False)

    if queryset.model is Project:
        if client:
            queryset = queryset.filter(contract_id=client)
        if manager:
            queryset = queryset.filter(manager_id=manager)
        if consultant:
            queryset = queryset.filter(tasks__assigned_to_id=consultant)
        return queryset.distinct()

    if queryset.model is Task:
        if client:
            queryset = queryset.filter(project__contract_id=client)
        if manager:
            queryset = queryset.filter(project__manager_id=manager)
        if consultant:
            queryset = queryset.filter(assigned_to_id=consultant)
        if not include_archived:
            queryset = queryset.filter(project__is_archived=False)
        return queryset.distinct()

    return queryset


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(PERCENT_QUANTIZER, rounding=ROUND_HALF_UP)


def _to_decimal(value: Decimal | None) -> Decimal:
    return value if value is not None else ZERO


def _percentage(numerator: Decimal, denominator: Decimal) -> Decimal:
    if not denominator:
        return ZERO
    return ((numerator / denominator) * Decimal("100")).quantize(
        PERCENT_QUANTIZER,
        rounding=ROUND_HALF_UP,
    )


def _project_timesheets(project: Project):
    return Timesheet.objects.filter(task__project=project)


def _project_totals(project: Project) -> dict[str, Decimal]:
    cost_expression = ExpressionWrapper(
        F("hours_worked") * F("user__hourly_cost"),
        output_field=COST_FIELD,
    )
    totals = _project_timesheets(project).aggregate(
        total_hours=Coalesce(Sum("hours_worked"), Value(ZERO), output_field=HOURS_FIELD),
        billable_hours=Coalesce(
            Sum(
                Case(
                    When(is_billable=True, then=F("hours_worked")),
                    default=Value(ZERO),
                    output_field=HOURS_FIELD,
                )
            ),
            Value(ZERO),
            output_field=HOURS_FIELD,
        ),
        internal_cost=Coalesce(Sum(cost_expression), Value(ZERO), output_field=COST_FIELD),
    )
    return {
        "total_hours": _to_decimal(totals["total_hours"]),
        "billable_hours": _to_decimal(totals["billable_hours"]),
        "internal_cost": _to_decimal(totals["internal_cost"]),
    }


def calculate_project_internal_cost(project: Project) -> Decimal:
    """Calcula o custo interno acumulado com base nas horas registradas."""
    return _project_totals(project)["internal_cost"]


def calculate_project_billability(project: Project) -> Decimal:
    """Retorna o percentual de horas faturáveis do projeto."""
    totals = _project_totals(project)
    return _percentage(totals["billable_hours"], totals["total_hours"])


def calculate_project_burn_rate(project: Project) -> Decimal:
    """Mede o percentual do orçamento já consumido pelo custo interno."""
    internal_cost = calculate_project_internal_cost(project)
    return _percentage(internal_cost, project.budget_allocated)


def calculate_project_profit_margin(project: Project) -> Decimal:
    """Calcula a margem de lucro realizada do projeto."""
    internal_cost = calculate_project_internal_cost(project)
    if not project.budget_allocated:
        return ZERO
    margin = ((project.budget_allocated - internal_cost) / project.budget_allocated) * Decimal("100")
    return _quantize(margin)


def _project_health(burn_rate: Decimal, profit_margin: Decimal) -> str:
    if burn_rate >= Decimal("90") or profit_margin <= Decimal("10"):
        return "Crítico"
    if burn_rate >= Decimal("70") or profit_margin <= Decimal("25"):
        return "Atenção"
    return "Saudável"


def get_dashboard_context() -> dict:
    """Monta o contexto usado pelo dashboard inicial do MVP."""
    active_projects = Project.objects.filter(contract__is_active=True, is_archived=False).select_related("contract")
    project_rows = []
    total_billable_hours = ZERO
    total_hours = ZERO
    total_internal_cost = ZERO
    total_budget = ZERO

    for project in active_projects:
        totals = _project_totals(project)
        project_total_hours = totals["total_hours"]
        project_billable_hours = totals["billable_hours"]
        internal_cost = totals["internal_cost"]
        burn_rate = _percentage(internal_cost, project.budget_allocated)
        profit_margin = _percentage(project.budget_allocated - internal_cost, project.budget_allocated)

        total_billable_hours += project_billable_hours
        total_hours += project_total_hours
        total_internal_cost += internal_cost
        total_budget += project.budget_allocated

        project_rows.append(
            {
                "project": project,
                "contract": project.contract,
                "total_hours": _quantize(project_total_hours),
                "billability": _percentage(project_billable_hours, project_total_hours),
                "internal_cost": _quantize(internal_cost),
                "burn_rate": burn_rate,
                "profit_margin": profit_margin,
                "health": _project_health(burn_rate, profit_margin),
            }
        )

    summary = {
        "billability": _percentage(total_billable_hours, total_hours),
        "burn_rate": _percentage(total_internal_cost, total_budget),
        "profit_margin": _percentage(total_budget - total_internal_cost, total_budget) if total_budget else ZERO,
        "active_projects": active_projects.count(),
    }
    return {"summary": summary, "projects": project_rows}


def _user_timesheet_totals(user: User) -> dict[str, Decimal]:
    totals = user.timesheets.aggregate(
        total_hours=Coalesce(Sum("hours_worked"), Value(ZERO), output_field=HOURS_FIELD),
        billable_hours=Coalesce(
            Sum(
                Case(
                    When(is_billable=True, then=F("hours_worked")),
                    default=Value(ZERO),
                    output_field=HOURS_FIELD,
                )
            ),
            Value(ZERO),
            output_field=HOURS_FIELD,
        ),
    )
    total_hours = _to_decimal(totals["total_hours"])
    billable_hours = _to_decimal(totals["billable_hours"])
    return {
        "total_hours": total_hours,
        "billable_hours": billable_hours,
        "billability": _percentage(billable_hours, total_hours),
    }


def get_projects_overview(filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """Retorna uma visão resumida dos projetos ativos para as telas gerenciais."""
    health_map = {row["project"].id: row for row in get_dashboard_context()["projects"]}
    projects = _apply_management_filters(
        Project.objects.filter(contract__is_active=True).select_related("contract", "manager").prefetch_related(
            "tasks__assigned_to"
        ),
        filters,
    )
    rows = []

    for project in projects:
        task_stats = project.tasks.aggregate(
            total_tasks=Count("id"),
            completed_tasks=Count("id", filter=Q(is_completed=True)),
            pending_approval_tasks=Count("id", filter=Q(is_completed=False, completion_requested_at__isnull=False)),
        )
        related_consultants = [
            task.assigned_to.get_full_name() or task.assigned_to.username
            for task in project.tasks.all()
            if task.assigned_to is not None
        ]
        unique_consultants = list(dict.fromkeys(related_consultants))
        project_health = health_map.get(project.id, {})
        total_tasks = task_stats["total_tasks"] or 0
        completed_tasks = task_stats["completed_tasks"] or 0
        pending_approval_tasks = task_stats["pending_approval_tasks"] or 0
        progress = _percentage(Decimal(completed_tasks), Decimal(total_tasks)) if total_tasks else ZERO

        rows.append(
            {
                "project": project,
                "client_name": project.contract.client_name,
                "manager_name": project.manager.get_full_name() or project.manager.username if project.manager else "Sem gerente",
                "health": project_health.get("health", "Sem dados"),
                "billability": project_health.get("billability", ZERO),
                "burn_rate": project_health.get("burn_rate", ZERO),
                "profit_margin": project_health.get("profit_margin", ZERO),
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "pending_approval_tasks": pending_approval_tasks,
                "progress": progress,
                "consultants": unique_consultants,
            }
        )

    return rows


def get_pending_task_approvals(filters: dict[str, str] | None = None) -> list[Task]:
    """Retorna tarefas aguardando validação por um perfil de gestão."""

    return list(
        _apply_management_filters(
            Task.objects.filter(is_completed=False, completion_requested_at__isnull=False)
            .select_related("project", "project__contract", "project__manager", "assigned_to", "completion_requested_by"),
            filters,
        )
        .order_by("completion_requested_at", "project__name", "name")
    )


def get_management_task_board(filters: dict[str, str] | None = None) -> list[Task]:
    """Lista tarefas operacionais com status para acompanhamento gerencial."""

    return list(
        _apply_management_filters(
            Task.objects.select_related(
                "project",
                "project__contract",
                "project__manager",
                "assigned_to",
                "completion_requested_by",
                "completion_validated_by",
            ),
            filters,
        ).order_by("project__name", "name")
    )


def get_management_filter_options() -> dict[str, list[Any]]:
    """Retorna opções de filtro para a tela gerencial de projetos."""

    return {
        "clients": list(Contract.objects.filter(is_active=True).order_by("client_name")),
        "managers": list(User.objects.filter(role=UserRole.MANAGER, is_active=True).order_by("first_name", "username")),
        "consultants": list(User.objects.filter(role=UserRole.CONSULTANT, is_active=True).order_by("first_name", "username")),
    }


def get_team_overview() -> list[dict[str, Any]]:
    """Monta um resumo do banco de talentos para telas de gestão."""
    consultants = User.objects.filter(role=UserRole.CONSULTANT, is_active=True).prefetch_related(
        "user_skills__skill",
        "assigned_tasks",
        "timesheets",
    )
    rows = []

    for consultant in consultants:
        totals = _user_timesheet_totals(consultant)
        skills = [link.skill.name for link in consultant.user_skills.all()]
        rows.append(
            {
                "user": consultant,
                "skills": skills,
                "assigned_tasks": consultant.assigned_tasks.count(),
                "hours_worked": totals["total_hours"],
                "billability": totals["billability"],
            }
        )

    return rows


def get_role_dashboard_context(user: User) -> dict[str, Any]:
    """Adapta o conteúdo do dashboard de acordo com o papel do usuário."""
    context = get_dashboard_context()
    context.update(
        {
            "dashboard_role": user.role,
            "role_label": user.get_role_display(),
            "active_contracts": Contract.objects.filter(is_active=True).count(),
        }
    )

    if user.role == UserRole.CONSULTANT:
        user_totals = _user_timesheet_totals(user)
        assigned_tasks = Task.objects.filter(assigned_to=user, is_archived=False, project__is_archived=False).select_related(
            "project",
            "project__contract",
            "completion_requested_by",
            "completion_validated_by",
        )
        recent_entries = user.timesheets.select_related("task", "task__project").order_by("-date")[:5]
        context.update(
            {
                "hero_title": "Seu painel operacional",
                "hero_description": "Acompanhe suas tarefas, seu ritmo de lançamento e mantenha seus apontamentos em dia.",
                "personal_summary": user_totals,
                "assigned_tasks": assigned_tasks,
                "recent_entries": recent_entries,
                "pending_approval_count": assigned_tasks.filter(completion_requested_at__isnull=False, is_completed=False).count(),
                "completed_tasks_count": assigned_tasks.filter(is_completed=True).count(),
            }
        )
        return context

    management_context = {
        "hero_title": "Visão integrada da operação",
        "hero_description": "Monitore contratos, saúde dos projetos e capacidade da equipe em uma única tela.",
        "projects_overview": get_projects_overview(),
        "pending_task_approvals": get_pending_task_approvals(),
        "team_overview": get_team_overview(),
        "consultants_count": User.objects.filter(role=UserRole.CONSULTANT, is_active=True).count(),
    }

    if user.role == UserRole.ADMIN:
        management_context.update(
            {
                "hero_title": "Painel administrativo da plataforma",
                "hero_description": "Acompanhe operação, equipe e gestão da base antes de avançar para o admin detalhado.",
                "users_count": User.objects.count(),
            }
        )

    context.update(management_context)
    return context
