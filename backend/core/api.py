"""Endpoints de API REST (JSON) para consumo assíncrono do frontend e integrações.

Atende às diretrizes do Projeto Integrador II:
- Fornecimento e consumo de dados em JSON
- Respostas semânticas com status codes HTTP apropriados (200, 201, 400, 403, 404)
- Tratamento seguro de CSRF e permissões por perfil
"""

from __future__ import annotations

import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from .forms import TimesheetForm
from .models import Project, Task, Timesheet, UserRole
from .services import get_role_dashboard_context


def _json_error(message: str, errors: dict | None = None, status: int = 400) -> JsonResponse:
    """Helper para retorno padronizado de erros JSON."""
    payload: dict[str, object] = {
        "success": False,
        "message": message,
    }
    if errors:
        payload["errors"] = errors
    return JsonResponse(payload, status=status)


@login_required
@require_http_methods(["POST"])
def api_timesheet_create_view(request: HttpRequest) -> JsonResponse:
    """Cria um registro de horas (Timesheet) via requisição assíncrona (JSON ou FormData).

    Retorna status 201 em caso de sucesso ou 400 com os erros de validação.
    """
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _json_error("Payload JSON inválido.", status=400)
    else:
        data = request.POST

    form = TimesheetForm(data, current_user=request.user)
    if not form.is_valid():
        formatted_errors = {
            field: [err["message"] for err in err_list]
            for field, err_list in form.errors.get_json_data().items()
        }
        return _json_error(
            "Não foi possível salvar o lançamento. Verifique os campos destacados.",
            errors=formatted_errors,
            status=400,
        )

    entry = form.save()
    user_name = entry.user.get_full_name() or entry.user.username

    return JsonResponse(
        {
            "success": True,
            "message": "Lançamento registrado com sucesso!",
            "entry": {
                "id": entry.id,
                "user": user_name,
                "project": entry.task.project.name,
                "task": entry.task.name,
                "date": entry.date.strftime("%d/%m/%Y"),
                "hours_worked": f"{entry.hours_worked:.2f}".replace(".", ","),
                "is_billable": entry.is_billable,
                "description": entry.description,
            },
        },
        status=201,
    )


@login_required
@require_http_methods(["POST"])
def api_task_request_completion_view(request: HttpRequest, task_id: int) -> JsonResponse:
    """Permite ao consultor responsável solicitar assincronamente a validação da tarefa."""
    task = get_object_or_404(Task.objects.select_related("assigned_to", "project"), pk=task_id)

    if request.user.role != UserRole.CONSULTANT or task.assigned_to_id != request.user.id:
        return _json_error(
            "Você só pode solicitar validação das tarefas atribuídas a você.",
            status=403,
        )

    if task.is_completed:
        return _json_error("Esta tarefa já foi validada e concluída.", status=400)

    if task.completion_requested_at is not None:
        return _json_error("Esta tarefa já está aguardando validação da gestão.", status=400)

    task.request_completion(requested_by=request.user)

    return JsonResponse(
        {
            "success": True,
            "message": "Solicitação de validação enviada com sucesso à gerência.",
            "task": {
                "id": task.id,
                "name": task.name,
                "workflow_state": "in_validation",
                "workflow_label": "Em validação (Aguardando homologação da gerência)",
            },
        },
        status=200,
    )


@login_required
@require_http_methods(["GET"])
def api_dashboard_metrics_view(request: HttpRequest) -> JsonResponse:
    """Retorna métricas consolidadas em JSON para renderização dinâmica no frontend (Chart.js)."""
    context = get_role_dashboard_context(request.user)
    summary = context.get("summary", {})
    projects = context.get("projects", [])

    if request.user.role == UserRole.CONSULTANT:
        personal = context.get("personal_summary", {})
        billability_val = float(personal.get("billability", 0))
        total_hours = float(personal.get("total_hours", 0))
        billable_hours = float(personal.get("billable_hours", 0))
        non_billable_hours = max(0.0, total_hours - billable_hours)
    else:
        billability_val = float(summary.get("billability", 0))
        total_hours = float(summary.get("total_hours", 0))
        billable_hours = float(summary.get("total_billable_hours", 0))
        non_billable_hours = max(0.0, total_hours - billable_hours)

    non_billable_percent = max(0.0, round(100.0 - billability_val, 2)) if total_hours > 0 else 0.0

    project_labels = [row["project"].name for row in projects]
    burn_rates = [float(row["burn_rate"]) for row in projects]
    profit_margins = [float(row["profit_margin"]) for row in projects]
    health_statuses = [row["health"] for row in projects]

    return JsonResponse(
        {
            "success": True,
            "role": request.user.role,
            "metrics": {
                "billability_rate": str(summary.get("billability", billability_val)),
                "burn_rate": str(summary.get("burn_rate", 0)),
                "profit_margin": str(summary.get("profit_margin", 0)),
                "active_projects_count": summary.get("active_projects", len(projects)),
                "consultants_count": context.get("consultants_count", 0),
            },
            "charts": {
                "billability": {
                    "billable_percent": billability_val,
                    "non_billable_percent": non_billable_percent,
                    "billable_hours": billable_hours,
                    "non_billable_hours": non_billable_hours,
                    "total_hours": total_hours,
                },
                "projects_burn_rate": {
                    "labels": project_labels,
                    "burn_rates": burn_rates,
                    "profit_margins": profit_margins,
                    "health_statuses": health_statuses,
                },
            },
        },
        status=200,
    )
