"""Views do app principal, incluindo autenticação de entrada e páginas do MVP."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import (
    ProjectManagementForm,
    ProjectUpdateForm,
    TaskManagementForm,
    TaskUpdateForm,
    TimesheetForm,
)
from .models import Project, Task, Timesheet, UserRole
from .services import (
    get_management_filter_options,
    get_management_task_board,
    get_pending_task_approvals,
    get_projects_overview,
    get_role_dashboard_context,
    get_team_overview,
)


def _is_management_user(request: HttpRequest) -> bool:
    return request.user.role in {UserRole.ADMIN, UserRole.MANAGER}


def _build_navigation(request: HttpRequest) -> list[dict[str, str | bool]]:
    items = [
        {
            "label": "Dashboard",
            "url": reverse("core:dashboard"),
            "page": "dashboard",
            "visible": True,
        },
        {
            "label": "Projetos",
            "url": reverse("core:projects"),
            "page": "projects",
            "visible": _is_management_user(request),
        },
        {
            "label": "Talentos",
            "url": reverse("core:talent_bank"),
            "page": "talent_bank",
            "visible": _is_management_user(request),
        },
        {
            "label": "Registro de Horas",
            "url": reverse("core:timesheet"),
            "page": "timesheet",
            "visible": True,
        },
    ]
    return [item for item in items if item["visible"]]


def _base_context(request: HttpRequest, page_name: str, page_title: str) -> dict[str, object]:
    return {
        "page_name": page_name,
        "page_title": page_title,
        "navigation_items": _build_navigation(request),
        "role_label": request.user.get_role_display() if request.user.is_authenticated else "Visitante",
    }


def _ensure_management_access(request: HttpRequest) -> HttpResponse | None:
    if not _is_management_user(request):
        messages.warning(request, "Seu perfil não possui acesso a esta área.")
        return redirect("core:dashboard")
    return None


def _recent_timesheets_for(request: HttpRequest):
    queryset = Timesheet.objects.select_related("user", "task", "task__project").order_by("-date", "-id")
    if request.user.role == UserRole.CONSULTANT:
        return queryset.filter(user=request.user)[:10]
    return queryset[:10]


def _redirect_back(request: HttpRequest, fallback_name: str) -> HttpResponse:
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    return redirect(fallback_name)


def _projects_page_context(
    request: HttpRequest,
    *,
    project_form: ProjectManagementForm | None = None,
    task_form: TaskManagementForm | None = None,
    project_update_form: ProjectUpdateForm | None = None,
    task_update_form: TaskUpdateForm | None = None,
) -> dict[str, object]:
    """Monta o contexto consolidado da área de projetos para perfis gerenciais."""

    selected_filters = {
        "client": request.GET.get("client", ""),
        "manager": request.GET.get("manager", ""),
        "consultant": request.GET.get("consultant", ""),
        "include_archived": request.GET.get("include_archived", ""),
    }
    context = {
        "projects_overview": get_projects_overview(selected_filters),
        "task_board": get_management_task_board(selected_filters),
        "pending_task_approvals": get_pending_task_approvals(selected_filters),
        "project_form": project_form or ProjectManagementForm(),
        "task_form": task_form or TaskManagementForm(),
        "project_update_form": project_update_form or ProjectUpdateForm(),
        "task_update_form": task_update_form or TaskUpdateForm(),
        "management_filters": selected_filters,
    }
    context.update(get_management_filter_options())
    context.update(_base_context(request, "projects", "Portfólio de Projetos"))
    return context


def home_redirect_view(request: HttpRequest) -> HttpResponse:
    """Redireciona a raiz para login ou dashboard conforme a autenticação."""
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    return redirect("core:login")


@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """Renderiza o dashboard principal com os indicadores agregados."""
    context = get_role_dashboard_context(request.user)
    context.update(_base_context(request, "dashboard", "Dashboard"))
    return render(request, "core/index.html", context)


@login_required
def projects_view(request: HttpRequest) -> HttpResponse:
    """Exibe a visão consolidada de projetos para perfis gerenciais."""
    redirect_response = _ensure_management_access(request)
    if redirect_response is not None:
        return redirect_response
    return render(request, "core/projects.html", _projects_page_context(request))


@login_required
def project_create_view(request: HttpRequest) -> HttpResponse:
    """Permite a perfis gerenciais cadastrar projetos sem usar o Django Admin."""

    if request.method != "POST":
        return redirect("core:projects")

    redirect_response = _ensure_management_access(request)
    if redirect_response is not None:
        return redirect_response

    project_form = ProjectManagementForm(request.POST)
    task_form = TaskManagementForm()
    project_update_form = ProjectUpdateForm()
    task_update_form = TaskUpdateForm()
    if project_form.is_valid():
        project = project_form.save()
        messages.success(request, f"Projeto '{project.name}' criado com sucesso.")
        return _redirect_back(request, "core:projects")

    messages.warning(request, "Não foi possível criar o projeto. Revise os campos destacados.")
    return render(
        request,
        "core/projects.html",
        _projects_page_context(
            request,
            project_form=project_form,
            task_form=task_form,
            project_update_form=project_update_form,
            task_update_form=task_update_form,
        ),
    )


@login_required
def task_create_view(request: HttpRequest) -> HttpResponse:
    """Permite a perfis gerenciais cadastrar tarefas e atribuir responsáveis."""

    if request.method != "POST":
        return redirect("core:projects")

    redirect_response = _ensure_management_access(request)
    if redirect_response is not None:
        return redirect_response

    project_form = ProjectManagementForm()
    task_form = TaskManagementForm(request.POST)
    project_update_form = ProjectUpdateForm()
    task_update_form = TaskUpdateForm()
    if task_form.is_valid():
        task = task_form.save()
        messages.success(request, f"Tarefa '{task.name}' cadastrada com sucesso.")
        return _redirect_back(request, "core:projects")

    messages.warning(request, "Não foi possível criar a tarefa. Revise os campos destacados.")
    return render(
        request,
        "core/projects.html",
        _projects_page_context(
            request,
            project_form=project_form,
            task_form=task_form,
            project_update_form=project_update_form,
            task_update_form=task_update_form,
        ),
    )


@login_required
def project_update_view(request: HttpRequest) -> HttpResponse:
    """Permite a perfis gerenciais ajustar orçamento e nome de projetos existentes."""

    if request.method != "POST":
        return redirect("core:projects")

    redirect_response = _ensure_management_access(request)
    if redirect_response is not None:
        return redirect_response

    project_form = ProjectManagementForm()
    task_form = TaskManagementForm()
    project_update_form = ProjectUpdateForm(request.POST)
    task_update_form = TaskUpdateForm()
    if project_update_form.is_valid():
        project = project_update_form.save()
        messages.success(request, f"Projeto '{project.name}' atualizado com sucesso.")
        return _redirect_back(request, "core:projects")

    messages.warning(request, "Não foi possível atualizar o projeto. Revise os campos destacados.")
    return render(
        request,
        "core/projects.html",
        _projects_page_context(
            request,
            project_form=project_form,
            task_form=task_form,
            project_update_form=project_update_form,
            task_update_form=task_update_form,
        ),
    )


@login_required
def task_update_view(request: HttpRequest) -> HttpResponse:
    """Permite a perfis gerenciais reajustar responsável e horas estimadas da tarefa."""

    if request.method != "POST":
        return redirect("core:projects")

    redirect_response = _ensure_management_access(request)
    if redirect_response is not None:
        return redirect_response

    project_form = ProjectManagementForm()
    task_form = TaskManagementForm()
    project_update_form = ProjectUpdateForm()
    task_update_form = TaskUpdateForm(request.POST)
    if task_update_form.is_valid():
        task = task_update_form.save()
        messages.success(request, f"Tarefa '{task.name}' atualizada com sucesso.")
        return _redirect_back(request, "core:projects")

    messages.warning(request, "Não foi possível atualizar a tarefa. Revise os campos destacados.")
    return render(
        request,
        "core/projects.html",
        _projects_page_context(
            request,
            project_form=project_form,
            task_form=task_form,
            project_update_form=project_update_form,
            task_update_form=task_update_form,
        ),
    )


@login_required
def project_archive_view(request: HttpRequest, project_id: int) -> HttpResponse:
    """Arquiva um projeto sem excluir seu histórico operacional."""

    if request.method != "POST":
        return redirect("core:projects")

    redirect_response = _ensure_management_access(request)
    if redirect_response is not None:
        return redirect_response

    project = get_object_or_404(Project, pk=project_id)
    project.archive()
    messages.success(request, f"Projeto '{project.name}' arquivado com sucesso.")
    return _redirect_back(request, "core:projects")


@login_required
def project_restore_view(request: HttpRequest, project_id: int) -> HttpResponse:
    """Reativa um projeto arquivado para voltar à carteira operacional."""

    if request.method != "POST":
        return redirect("core:projects")

    redirect_response = _ensure_management_access(request)
    if redirect_response is not None:
        return redirect_response

    project = get_object_or_404(Project, pk=project_id)
    project.restore()
    messages.success(request, f"Projeto '{project.name}' reativado com sucesso.")
    return _redirect_back(request, "core:projects")


@login_required
def task_archive_view(request: HttpRequest, task_id: int) -> HttpResponse:
    """Arquiva uma tarefa sem apagar seu histórico de execução."""

    if request.method != "POST":
        return redirect("core:projects")

    redirect_response = _ensure_management_access(request)
    if redirect_response is not None:
        return redirect_response

    task = get_object_or_404(Task, pk=task_id)
    task.archive()
    messages.success(request, f"Tarefa '{task.name}' arquivada com sucesso.")
    return _redirect_back(request, "core:projects")


@login_required
def task_restore_view(request: HttpRequest, task_id: int) -> HttpResponse:
    """Reativa uma tarefa arquivada para voltar ao board operacional."""

    if request.method != "POST":
        return redirect("core:projects")

    redirect_response = _ensure_management_access(request)
    if redirect_response is not None:
        return redirect_response

    task = get_object_or_404(Task, pk=task_id)
    task.restore()
    messages.success(request, f"Tarefa '{task.name}' reativada com sucesso.")
    return _redirect_back(request, "core:projects")


@login_required
def talent_bank_view(request: HttpRequest) -> HttpResponse:
    """Exibe o banco de talentos para administradores e gerentes."""
    redirect_response = _ensure_management_access(request)
    if redirect_response is not None:
        return redirect_response
    context = {
        "team_overview": get_team_overview(),
    }
    context.update(_base_context(request, "talent_bank", "Banco de Talentos"))
    return render(request, "core/talent_bank.html", context)


@login_required
def timesheet_create_view(request: HttpRequest) -> HttpResponse:
    """Exibe e processa o formulário simples de lançamento de horas."""
    if request.method == "POST":
        form = TimesheetForm(request.POST, current_user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Lançamento registrado com sucesso.")
            return redirect("core:timesheet")
    else:
        form = TimesheetForm(current_user=request.user)

    recent_entries = _recent_timesheets_for(request)
    context = {
        "form": form,
        "recent_entries": recent_entries,
        "is_consultant": request.user.role == UserRole.CONSULTANT,
    }
    context.update(_base_context(request, "timesheet", "Registro de Horas"))
    return render(request, "core/timesheet.html", context)


@login_required
def task_request_completion_view(request: HttpRequest, task_id: int) -> HttpResponse:
    """Permite ao responsável pela tarefa solicitar sua validação."""

    if request.method != "POST":
        return redirect("core:dashboard")

    task = get_object_or_404(Task.objects.select_related("assigned_to"), pk=task_id)
    if request.user.role != UserRole.CONSULTANT or task.assigned_to_id != request.user.id:
        messages.warning(request, "Você só pode solicitar conclusão das suas próprias tarefas.")
        return _redirect_back(request, "core:dashboard")

    if task.is_completed:
        messages.info(request, "Essa tarefa já foi validada como concluída.")
        return _redirect_back(request, "core:dashboard")

    if task.completion_requested_at is not None:
        messages.info(request, "Essa tarefa já está aguardando validação da gestão.")
        return _redirect_back(request, "core:dashboard")

    task.request_completion(requested_by=request.user)
    messages.success(request, "Conclusão enviada para validação da gestão.")
    return _redirect_back(request, "core:dashboard")


@login_required
def task_validate_completion_view(request: HttpRequest, task_id: int) -> HttpResponse:
    """Permite a um perfil de gestão validar a conclusão de uma tarefa."""

    if request.method != "POST":
        return redirect("core:projects")

    redirect_response = _ensure_management_access(request)
    if redirect_response is not None:
        return redirect_response

    task = get_object_or_404(Task, pk=task_id)
    task.validate_completion(validated_by=request.user)
    messages.success(request, "Tarefa validada e contabilizada como concluída.")
    return _redirect_back(request, "core:projects")


@login_required
def task_reopen_view(request: HttpRequest, task_id: int) -> HttpResponse:
    """Permite a um perfil de gestão devolver a tarefa para execução."""

    if request.method != "POST":
        return redirect("core:projects")

    redirect_response = _ensure_management_access(request)
    if redirect_response is not None:
        return redirect_response

    task = get_object_or_404(Task, pk=task_id)
    task.reopen()
    messages.success(request, "Tarefa reaberta para nova execução/ajustes.")
    return _redirect_back(request, "core:projects")


def healthcheck_view(request: HttpRequest) -> JsonResponse:
    """Retorna um payload mínimo para verificação de saúde do serviço."""
    return JsonResponse({"status": "ok", "service": "fcn-ti-backend"})
