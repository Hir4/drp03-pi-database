from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import Contract, ProficiencyLevel, Project, Skill, Task, Timesheet, User, UserRole

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


RISK_GAP_HIGH = Decimal("20")
RISK_GAP_WARNING = Decimal("10")


def delivery_risk(burn_rate: Decimal, progress: Decimal) -> dict[str, Any]:
    """Compara orçamento consumido com tarefas concluídas (ritmo de entrega).

    Usado pela tela de Projetos, pelo dashboard gerencial e pela tela de
    Análises, para que as três mostrem a mesma classificação.
    """
    gap = burn_rate - progress
    if gap >= RISK_GAP_HIGH:
        level, label = "high", "Em risco"
    elif gap >= RISK_GAP_WARNING:
        level, label = "warning", "Atenção"
    else:
        level, label = "ok", "No ritmo"
    return {"risk_level": level, "risk_label": label, "gap": gap}


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
        "total_hours": total_hours,
        "total_billable_hours": total_billable_hours,
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
        # Tarefas arquivadas ficam fora do progresso, como na tela de Análises.
        task_stats = project.tasks.filter(is_archived=False).aggregate(
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
        project_health = health_map.get(project.id)
        if project_health is None:
            totals = _project_totals(project)
            burn_rate = _percentage(totals["internal_cost"], project.budget_allocated)
            profit_margin = _percentage(project.budget_allocated - totals["internal_cost"], project.budget_allocated)
            project_health = {
                "health": _project_health(burn_rate, profit_margin),
                "billability": _percentage(totals["billable_hours"], totals["total_hours"]),
                "burn_rate": burn_rate,
                "profit_margin": profit_margin,
            }
        total_tasks = task_stats["total_tasks"] or 0
        completed_tasks = task_stats["completed_tasks"] or 0
        pending_approval_tasks = task_stats["pending_approval_tasks"] or 0
        progress = _percentage(Decimal(completed_tasks), Decimal(total_tasks)) if total_tasks else ZERO

        rows.append(
            {
                "project": project,
                "client_name": project.contract.client_name,
                "manager_name": project.manager.get_full_name() or project.manager.username if project.manager else "Sem gerente",
                "health": project_health["health"],
                "billability": project_health["billability"],
                "burn_rate": project_health["burn_rate"],
                "profit_margin": project_health["profit_margin"],
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "pending_approval_tasks": pending_approval_tasks,
                "progress": progress,
                "consultants": unique_consultants,
                **delivery_risk(project_health["burn_rate"], progress),
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


WEEKLY_HOURS_TARGET = Decimal("40")
RECENT_LOAD_WEEKS = 4
PROFICIENCY_ORDER = {
    ProficiencyLevel.BASIC: 1,
    ProficiencyLevel.INTERMEDIATE: 2,
    ProficiencyLevel.ADVANCED: 3,
    ProficiencyLevel.EXPERT: 4,
}


def _hours_between(user: User, start: date, end: date) -> dict[str, Decimal]:
    """Horas totais e faturáveis de uma pessoa entre duas datas (inclusive)."""
    totals = Timesheet.objects.filter(user=user, date__gte=start, date__lte=end).aggregate(
        total_hours=Coalesce(Sum("hours_worked"), Value(ZERO), output_field=HOURS_FIELD),
        billable_hours=Coalesce(
            Sum(Case(When(is_billable=True, then=F("hours_worked")), default=Value(ZERO), output_field=HOURS_FIELD)),
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


def get_user_hours_snapshot(user: User, today: date | None = None) -> dict[str, Any]:
    """Horas de hoje e da semana corrente (segunda a hoje) com a meta semanal."""
    today = today or timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    week = _hours_between(user, week_start, today)
    return {
        "today": today,
        "today_hours": _hours_between(user, today, today)["total_hours"],
        "week_hours": week["total_hours"],
        "week_target": WEEKLY_HOURS_TARGET,
        "week_progress": min(Decimal("100"), _percentage(week["total_hours"], WEEKLY_HOURS_TARGET)),
    }


def get_personal_weekly_hours(user: User, today: date | None = None, weeks: int = 8) -> dict[str, list]:
    """Série semanal (faturáveis x não faturáveis) das últimas ``weeks`` semanas de uma pessoa."""
    today = today or timezone.localdate()
    current_week = today - timedelta(days=today.weekday())
    starts = [current_week - timedelta(weeks=offset) for offset in range(weeks - 1, -1, -1)]
    rows = (
        Timesheet.objects.filter(user=user, date__gte=starts[0], date__lte=today)
        .values("date", "is_billable")
        .annotate(hours=Sum("hours_worked"))
        .order_by()
    )
    buckets = {start: [ZERO, ZERO] for start in starts}
    for row in rows:
        start = row["date"] - timedelta(days=row["date"].weekday())
        if start in buckets:
            buckets[start][0 if row["is_billable"] else 1] += row["hours"] or ZERO
    return {
        "labels": [f"{start:%d/%m}" for start in starts],
        "billable_hours": [float(values[0]) for values in buckets.values()],
        "non_billable_hours": [float(values[1]) for values in buckets.values()],
        "target": float(WEEKLY_HOURS_TARGET),
    }


def _load_level(utilization: Decimal) -> tuple[str, str]:
    if utilization >= Decimal("85"):
        return "high", "Carga alta"
    if utilization >= Decimal("50"):
        return "balanced", "Carga equilibrada"
    return "available", "Disponível"


def get_skill_filter_options() -> dict[str, list[Any]]:
    """Opções do filtro do Banco de Talentos."""
    return {
        "skills": list(Skill.objects.order_by("name")),
        "proficiency_levels": ProficiencyLevel.choices,
    }


def get_team_overview(filters: dict[str, str] | None = None, today: date | None = None) -> list[dict[str, Any]]:
    """Banco de talentos: competências com nível, carga recente e tarefas abertas.

    A carga considera as últimas ``RECENT_LOAD_WEEKS`` semanas contra a meta de
    40h semanais. A lista sai ordenada da pessoa mais disponível para a mais
    carregada, que é a pergunta típica de quem vai alocar alguém.

    Filtros aceitos: ``skill`` (id), ``level`` (nível mínimo na skill
    escolhida) e ``q`` (busca por nome ou usuário).
    """
    filters = filters or {}
    today = today or timezone.localdate()
    recent_start = today - timedelta(weeks=RECENT_LOAD_WEEKS) + timedelta(days=1)
    capacity = WEEKLY_HOURS_TARGET * RECENT_LOAD_WEEKS

    consultants = User.objects.filter(role=UserRole.CONSULTANT, is_active=True).prefetch_related(
        "user_skills__skill",
        "assigned_tasks",
    )
    search = (filters.get("q") or "").strip()
    if search:
        consultants = consultants.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(username__icontains=search)
        )

    skill_id = filters.get("skill") or ""
    min_level = PROFICIENCY_ORDER.get(filters.get("level") or "", 0)

    rows = []
    for consultant in consultants:
        links = sorted(
            consultant.user_skills.all(),
            key=lambda link: (-PROFICIENCY_ORDER.get(link.proficiency, 0), link.skill.name),
        )
        if skill_id:
            match = next((link for link in links if str(link.skill_id) == str(skill_id)), None)
            if match is None or PROFICIENCY_ORDER.get(match.proficiency, 0) < min_level:
                continue

        totals = _user_timesheet_totals(consultant)
        recent = _hours_between(consultant, recent_start, today)
        utilization = _percentage(recent["total_hours"], capacity)
        load_level, load_label = _load_level(utilization)
        open_tasks = sum(
            1 for task in consultant.assigned_tasks.all() if not task.is_completed and not task.is_archived
        )
        rows.append(
            {
                "user": consultant,
                "skills": [link.skill.name for link in links],
                "skill_levels": [
                    {
                        "name": link.skill.name,
                        "level": link.get_proficiency_display(),
                        "level_code": link.proficiency,
                        "matches_filter": str(link.skill_id) == str(skill_id),
                    }
                    for link in links
                ],
                "assigned_tasks": consultant.assigned_tasks.count(),
                "open_tasks": open_tasks,
                "hours_worked": totals["total_hours"],
                "billability": totals["billability"],
                "recent_hours": recent["total_hours"],
                "recent_billability": recent["billability"],
                "utilization": utilization,
                "utilization_bar": min(Decimal("100"), utilization),
                "load_level": load_level,
                "load_label": load_label,
            }
        )

    rows.sort(key=lambda row: (row["utilization"], row["user"].get_full_name() or row["user"].username))
    return rows


def _consultant_dashboard_context(user: User) -> dict[str, Any]:
    """Painel do consultor: apenas dados próprios (sem finanças da empresa)."""
    today = timezone.localdate()
    snapshot = get_user_hours_snapshot(user, today)
    last_30_days = _hours_between(user, today - timedelta(days=29), today)
    assigned_tasks = (
        Task.objects.filter(assigned_to=user, is_archived=False, project__is_archived=False)
        .select_related("project", "project__contract", "completion_requested_by", "completion_validated_by")
        .annotate(logged_hours=Coalesce(Sum("timesheets__hours_worked"), Value(ZERO), output_field=HOURS_FIELD))
        .order_by("is_completed", "completion_requested_at", "project__name", "name")
    )
    tasks = list(assigned_tasks)
    for task in tasks:
        task.estimate_usage = _percentage(task.logged_hours, task.estimated_hours) if task.estimated_hours else ZERO
        task.estimate_usage_bar = min(Decimal("100"), task.estimate_usage)
        task.over_estimate = task.estimated_hours and task.logged_hours > task.estimated_hours

    return {
        "hero_title": "Seu painel operacional",
        "hero_description": "Suas tarefas, suas horas da semana e o que precisa de atenção hoje.",
        "hours_snapshot": snapshot,
        "personal_summary": _user_timesheet_totals(user),
        "personal_recent": last_30_days,
        "assigned_tasks": tasks,
        "open_tasks_count": sum(1 for task in tasks if not task.is_completed and task.completion_requested_at is None),
        "recent_entries": user.timesheets.select_related("task", "task__project").order_by("-date", "-id")[:5],
        "pending_approval_count": sum(
            1 for task in tasks if task.completion_requested_at is not None and not task.is_completed
        ),
        "completed_tasks_count": sum(1 for task in tasks if task.is_completed),
    }


def get_role_dashboard_context(user: User) -> dict[str, Any]:
    """Adapta o conteúdo do dashboard de acordo com o papel do usuário.

    Consultores recebem só os próprios números; indicadores financeiros da
    carteira (burn rate, margem, orçamento) ficam restritos à gestão.
    """
    base = {
        "dashboard_role": user.role,
        "role_label": user.get_role_display(),
    }

    if user.role == UserRole.CONSULTANT:
        return {**base, **_consultant_dashboard_context(user)}

    context = get_dashboard_context()
    context.update(base)
    context["active_contracts"] = Contract.objects.filter(is_active=True).count()

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
