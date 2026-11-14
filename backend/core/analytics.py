"""Camada analítica da plataforma FCN TI (tela de Análises, API e relatório PDF).

Centraliza os cálculos para que a tela, a API ``/api/v1/analytics/`` e o
relatório de exportação mostrem sempre os mesmos números.

Regra de período:
- Métricas de fluxo (horas no tempo, carga da equipe, validações concluídas)
  respeitam as datas filtradas.
- Métricas acumuladas (estimado x realizado, risco dos projetos e orçamento x
  custo por cliente) usam todo o histórico, porque orçamento e estimativas não
  são distribuídos ao longo do tempo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Mapping

from django.db.models import Case, Count, ExpressionWrapper, F, Q, QuerySet, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import Contract, Project, Task, Timesheet, User, UserRole
from .services import COST_FIELD, HOURS_FIELD, ZERO, _percentage, _project_health, delivery_risk

MAX_WEEKLY_BUCKETS = 26
MONTH_LABELS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
SECONDS_PER_DAY = 86400
MIN_VALIDATION_WAIT_SECONDS = 60


@dataclass(frozen=True)
class AnalyticsFilters:
    """Filtros aceitos pela análise gerencial."""

    start: date | None = None
    end: date | None = None
    client_id: int | None = None
    manager_id: int | None = None

    def as_query_params(self) -> dict[str, str]:
        """Converte os filtros ativos em parâmetros de URL (para links e exportação)."""
        params: dict[str, str] = {}
        if self.start:
            params["start"] = self.start.isoformat()
        if self.end:
            params["end"] = self.end.isoformat()
        if self.client_id:
            params["client"] = str(self.client_id)
        if self.manager_id:
            params["manager"] = str(self.manager_id)
        return params


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------


def _parse_date(raw: Any) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(str(raw).strip())
    except ValueError:
        return None


def _parse_positive_int(raw: Any) -> int | None:
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def parse_analytics_filters(params: Mapping[str, Any]) -> AnalyticsFilters:
    """Lê os filtros da querystring, ignorando valores inválidos.

    Se a data inicial for posterior à final, as duas são trocadas.
    """
    start = _parse_date(params.get("start"))
    end = _parse_date(params.get("end"))
    if start and end and start > end:
        start, end = end, start
    return AnalyticsFilters(
        start=start,
        end=end,
        client_id=_parse_positive_int(params.get("client")),
        manager_id=_parse_positive_int(params.get("manager")),
    )


def describe_filters(filters: AnalyticsFilters) -> dict[str, str]:
    """Descreve os filtros em texto legível (cabeçalho do relatório)."""
    if filters.start and filters.end:
        period = f"{filters.start:%d/%m/%Y} a {filters.end:%d/%m/%Y}"
    elif filters.start:
        period = f"A partir de {filters.start:%d/%m/%Y}"
    elif filters.end:
        period = f"Até {filters.end:%d/%m/%Y}"
    else:
        period = "Todo o histórico"

    client = "Todos os clientes"
    if filters.client_id:
        contract = Contract.objects.filter(pk=filters.client_id).first()
        client = contract.client_name if contract else "Cliente não encontrado"

    manager = "Todos os gerentes"
    if filters.manager_id:
        user = User.objects.filter(pk=filters.manager_id).first()
        manager = (user.get_full_name() or user.username) if user else "Gerente não encontrado"

    return {"period": period, "client": client, "manager": manager}


# ---------------------------------------------------------------------------
# Escopo e agregações base
# ---------------------------------------------------------------------------


def _scoped_projects(filters: AnalyticsFilters) -> QuerySet[Project]:
    projects = Project.objects.filter(is_archived=False, contract__is_active=True)
    if filters.client_id:
        projects = projects.filter(contract_id=filters.client_id)
    if filters.manager_id:
        projects = projects.filter(manager_id=filters.manager_id)
    return projects


def _scoped_timesheets(filters: AnalyticsFilters, *, apply_period: bool = True) -> QuerySet[Timesheet]:
    timesheets = Timesheet.objects.filter(task__project__in=_scoped_projects(filters))
    if apply_period:
        if filters.start:
            timesheets = timesheets.filter(date__gte=filters.start)
        if filters.end:
            timesheets = timesheets.filter(date__lte=filters.end)
    return timesheets


def _cost_expression() -> ExpressionWrapper:
    return ExpressionWrapper(F("hours_worked") * F("user__hourly_cost"), output_field=COST_FIELD)


def _hours_aggregates() -> dict[str, Any]:
    return {
        "total_hours": Coalesce(Sum("hours_worked"), Value(ZERO), output_field=HOURS_FIELD),
        "billable_hours": Coalesce(
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
        "internal_cost": Coalesce(Sum(_cost_expression()), Value(ZERO), output_field=COST_FIELD),
    }


def _to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return round(float(value), 2)


def _project_costs(project_ids: list[int]) -> dict[int, Decimal]:
    """Custo interno acumulado (horas x custo/hora) de cada projeto."""
    rows = (
        Timesheet.objects.filter(task__project_id__in=project_ids)
        .values_list("task__project_id")
        .annotate(cost=Sum(_cost_expression()))
        .order_by()
    )
    return {project_id: cost or ZERO for project_id, cost in rows}


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------


def period_kpis(filters: AnalyticsFilters) -> dict[str, Any]:
    """Totais de horas, billability e custo interno no período filtrado."""
    totals = _scoped_timesheets(filters).aggregate(**_hours_aggregates())
    total_hours = totals["total_hours"] or ZERO
    billable_hours = totals["billable_hours"] or ZERO
    return {
        "total_hours": _to_float(total_hours),
        "billable_hours": _to_float(billable_hours),
        "non_billable_hours": _to_float(total_hours - billable_hours),
        "billability": _to_float(_percentage(billable_hours, total_hours)),
        "internal_cost": _to_float(totals["internal_cost"]),
        "active_projects": _scoped_projects(filters).count(),
    }


def _bucket_start(day: date, granularity: str) -> date:
    if granularity == "week":
        return day - timedelta(days=day.weekday())
    return day.replace(day=1)


def _next_bucket(day: date, granularity: str) -> date:
    if granularity == "week":
        return day + timedelta(days=7)
    return (day.replace(day=28) + timedelta(days=4)).replace(day=1)


def _bucket_label(day: date, granularity: str) -> str:
    if granularity == "week":
        return f"{day:%d/%m}"
    return f"{MONTH_LABELS[day.month - 1]}/{day.year}"


def hours_trend(filters: AnalyticsFilters) -> dict[str, Any]:
    """Horas faturáveis e não faturáveis agrupadas por semana (ou mês, em períodos longos).

    Semanas ou meses sem lançamentos aparecem com zero, para o eixo do tempo
    não esconder períodos parados.
    """
    rows = list(
        _scoped_timesheets(filters)
        .values("date", "is_billable")
        .annotate(hours=Sum("hours_worked"))
        .order_by()
    )
    empty = {
        "granularity": "week",
        "labels": [],
        "billable_hours": [],
        "non_billable_hours": [],
        "billability": [],
        "rows": [],
    }
    if not rows and not (filters.start and filters.end):
        return empty

    first = filters.start or min(row["date"] for row in rows)
    last = filters.end or max(row["date"] for row in rows)
    granularity = "week" if (last - first).days <= MAX_WEEKLY_BUCKETS * 7 else "month"

    buckets: dict[date, list[Decimal]] = {}
    cursor = _bucket_start(first, granularity)
    last_bucket = _bucket_start(last, granularity)
    while cursor <= last_bucket:
        buckets[cursor] = [ZERO, ZERO]
        cursor = _next_bucket(cursor, granularity)

    for row in rows:
        bucket = _bucket_start(row["date"], granularity)
        if bucket in buckets:
            buckets[bucket][0 if row["is_billable"] else 1] += row["hours"] or ZERO

    rows_out = [
        {
            "label": _bucket_label(day, granularity),
            "billable_hours": _to_float(values[0]),
            "non_billable_hours": _to_float(values[1]),
            "billability": _to_float(_percentage(values[0], values[0] + values[1])),
        }
        for day, values in sorted(buckets.items())
    ]
    return {
        "granularity": granularity,
        "labels": [row["label"] for row in rows_out],
        "billable_hours": [row["billable_hours"] for row in rows_out],
        "non_billable_hours": [row["non_billable_hours"] for row in rows_out],
        "billability": [row["billability"] for row in rows_out],
        "rows": rows_out,
    }


def estimate_vs_actual(filters: AnalyticsFilters) -> list[dict[str, Any]]:
    """Compara horas estimadas nas tarefas com as horas realmente lançadas (histórico completo)."""
    projects = list(_scoped_projects(filters).select_related("contract").order_by("name"))
    project_ids = [project.id for project in projects]
    estimated = dict(
        Task.objects.filter(project_id__in=project_ids, is_archived=False)
        .values_list("project_id")
        .annotate(total=Sum("estimated_hours"))
        .order_by()
    )
    actual = dict(
        Timesheet.objects.filter(task__project_id__in=project_ids, task__is_archived=False)
        .values_list("task__project_id")
        .annotate(total=Sum("hours_worked"))
        .order_by()
    )

    rows = []
    for project in projects:
        estimated_hours = estimated.get(project.id) or ZERO
        actual_hours = actual.get(project.id) or ZERO
        if not estimated_hours and not actual_hours:
            continue
        if estimated_hours:
            variance = _percentage(actual_hours - estimated_hours, estimated_hours)
            status = "Acima da estimativa" if variance > 0 else "Dentro da estimativa"
        else:
            variance = None
            status = "Sem estimativa"
        rows.append(
            {
                "project": project.name,
                "client": project.contract.client_name,
                "estimated_hours": _to_float(estimated_hours),
                "actual_hours": _to_float(actual_hours),
                "variance_percent": _to_float(variance) if variance is not None else None,
                "status": status,
            }
        )

    rows.sort(key=lambda row: (row["variance_percent"] is None, -(row["variance_percent"] or 0)))
    return rows


def project_risk(filters: AnalyticsFilters) -> list[dict[str, Any]]:
    """Cruza orçamento consumido com o avanço das tarefas para apontar projetos em risco.

    A diferença (``gap``) é o burn rate menos o progresso. Um projeto que já
    gastou bem mais orçamento do que entregou de tarefas aparece no topo.
    """
    projects = list(_scoped_projects(filters).select_related("contract", "manager").order_by("name"))
    project_ids = [project.id for project in projects]
    costs = _project_costs(project_ids)
    task_stats = {
        row["project_id"]: row
        for row in Task.objects.filter(project_id__in=project_ids, is_archived=False)
        .values("project_id")
        .annotate(total=Count("id"), done=Count("id", filter=Q(is_completed=True)))
        .order_by()
    }

    rows = []
    for project in projects:
        cost = costs.get(project.id, ZERO)
        stats = task_stats.get(project.id, {"total": 0, "done": 0})
        burn_rate = _percentage(cost, project.budget_allocated)
        progress = _percentage(Decimal(stats["done"]), Decimal(stats["total"])) if stats["total"] else ZERO
        margin = _percentage(project.budget_allocated - cost, project.budget_allocated)
        risk = delivery_risk(burn_rate, progress)

        manager = project.manager
        rows.append(
            {
                "project": project.name,
                "client": project.contract.client_name,
                "manager": (manager.get_full_name() or manager.username) if manager else "Sem gerente",
                "budget": _to_float(project.budget_allocated),
                "internal_cost": _to_float(cost),
                "burn_rate": _to_float(burn_rate),
                "progress": _to_float(progress),
                "gap": _to_float(risk["gap"]),
                "completed_tasks": stats["done"],
                "total_tasks": stats["total"],
                "risk_level": risk["risk_level"],
                "risk_label": risk["risk_label"],
                "health": _project_health(burn_rate, margin),
            }
        )

    rows.sort(key=lambda row: -row["gap"])
    return rows


def team_load(filters: AnalyticsFilters) -> list[dict[str, Any]]:
    """Horas por pessoa no período, separando faturáveis e não faturáveis.

    Sem filtro de cliente ou gerente, consultores ativos sem lançamentos também
    aparecem (com zero), para mostrar quem está ocioso.
    """
    totals = {
        row["user_id"]: row
        for row in _scoped_timesheets(filters).values("user_id").annotate(**_hours_aggregates()).order_by()
    }
    users = User.objects.filter(id__in=list(totals))
    if not (filters.client_id or filters.manager_id):
        users = User.objects.filter(Q(id__in=list(totals)) | Q(role=UserRole.CONSULTANT, is_active=True))

    rows = []
    for user in users:
        row = totals.get(user.id, {})
        total_hours = row.get("total_hours") or ZERO
        billable_hours = row.get("billable_hours") or ZERO
        rows.append(
            {
                "name": user.get_full_name() or user.username,
                "role": user.get_role_display(),
                "total_hours": _to_float(total_hours),
                "billable_hours": _to_float(billable_hours),
                "non_billable_hours": _to_float(total_hours - billable_hours),
                "billability": _to_float(_percentage(billable_hours, total_hours)),
            }
        )

    rows.sort(key=lambda row: (-row["total_hours"], row["name"]))
    return rows


def client_profitability(filters: AnalyticsFilters) -> list[dict[str, Any]]:
    """Orçamento dos projetos x custo interno acumulado, agrupado por cliente."""
    projects = list(_scoped_projects(filters).select_related("contract"))
    costs = _project_costs([project.id for project in projects])

    grouped: dict[int, dict[str, Any]] = {}
    for project in projects:
        entry = grouped.setdefault(
            project.contract_id,
            {"client": project.contract.client_name, "budget": ZERO, "cost": ZERO, "projects": 0},
        )
        entry["budget"] += project.budget_allocated
        entry["cost"] += costs.get(project.id, ZERO)
        entry["projects"] += 1

    rows = [
        {
            "client": entry["client"],
            "projects": entry["projects"],
            "budget": _to_float(entry["budget"]),
            "internal_cost": _to_float(entry["cost"]),
            "margin_value": _to_float(entry["budget"] - entry["cost"]),
            "margin_percent": _to_float(_percentage(entry["budget"] - entry["cost"], entry["budget"])),
        }
        for entry in grouped.values()
    ]
    rows.sort(key=lambda row: (row["margin_percent"], row["client"]))
    return rows


def validation_metrics(filters: AnalyticsFilters) -> dict[str, Any]:
    """Tempo entre o pedido de validação e a aprovação, e a fila pendente.

    As validações concluídas respeitam o período; a fila pendente mostra o que
    está aguardando agora, independentemente do período. Tarefas concluídas
    direto pela gestão, sem pedido prévio, não entram no tempo médio.
    """
    tasks = Task.objects.filter(project__in=_scoped_projects(filters), is_archived=False)

    validated = tasks.filter(
        is_completed=True,
        completion_requested_at__isnull=False,
        completion_validated_at__isnull=False,
    )
    if filters.start:
        validated = validated.filter(completion_validated_at__date__gte=filters.start)
    if filters.end:
        validated = validated.filter(completion_validated_at__date__lte=filters.end)

    # Conclusões feitas direto pela gestão (sem pedido do consultor) gravam pedido
    # e aprovação no mesmo instante; não medem espera e ficam fora da média.
    durations = [
        seconds
        for requested_at, validated_at in validated.values_list("completion_requested_at", "completion_validated_at")
        if (seconds := (validated_at - requested_at).total_seconds()) >= MIN_VALIDATION_WAIT_SECONDS
    ]
    average_seconds = sum(durations) / len(durations) if durations else None
    average_days = round(average_seconds / SECONDS_PER_DAY, 1) if average_seconds is not None else None
    average_hours = round(average_seconds / 3600, 1) if average_seconds is not None else None

    now = timezone.now()
    pending_tasks = (
        tasks.filter(is_completed=False, completion_requested_at__isnull=False)
        .select_related("project", "assigned_to")
        .order_by("completion_requested_at")
    )
    pending = [
        {
            "task": task.name,
            "project": task.project.name,
            "consultant": (task.assigned_to.get_full_name() or task.assigned_to.username) if task.assigned_to else "Sem responsável",
            "requested_at": timezone.localtime(task.completion_requested_at).strftime("%d/%m/%Y"),
            "waiting_days": round(max(0.0, (now - task.completion_requested_at).total_seconds()) / SECONDS_PER_DAY, 1),
        }
        for task in pending_tasks
    ]

    return {
        "validated_count": len(durations),
        "average_lead_time_days": average_days,
        "average_lead_time_hours": average_hours,
        "pending_count": len(pending),
        "oldest_pending_days": pending[0]["waiting_days"] if pending else None,
        "pending": pending[:10],
    }


def build_analytics_payload(filters: AnalyticsFilters) -> dict[str, Any]:
    """Monta todos os blocos da análise gerencial em um único dicionário serializável."""
    risk_rows = project_risk(filters)
    validation = validation_metrics(filters)
    kpis = period_kpis(filters)
    kpis.update(
        {
            "projects_at_risk": sum(1 for row in risk_rows if row["risk_level"] == "high"),
            "average_validation_days": validation["average_lead_time_days"],
            "average_validation_hours": validation["average_lead_time_hours"],
            "pending_validations": validation["pending_count"],
        }
    )
    return {
        "filters": {**filters.as_query_params(), **describe_filters(filters)},
        "kpis": kpis,
        "hours_trend": hours_trend(filters),
        "estimate_vs_actual": estimate_vs_actual(filters),
        "project_risk": risk_rows,
        "team_load": team_load(filters),
        "client_profitability": client_profitability(filters),
        "validation": validation,
    }
