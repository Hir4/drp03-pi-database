"""Rotas públicas e endpoints de API do app principal."""

from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .api import (
    api_analytics_view,
    api_dashboard_metrics_view,
    api_task_request_completion_view,
    api_timesheet_create_view,
)
from .views import (
    analytics_report_view,
    analytics_view,
    dashboard_view,
    healthcheck_view,
    home_redirect_view,
    project_archive_view,
    project_create_view,
    project_restore_view,
    project_update_view,
    projects_view,
    talent_bank_view,
    task_archive_view,
    task_create_view,
    task_reopen_view,
    task_request_completion_view,
    task_restore_view,
    task_update_view,
    task_validate_completion_view,
    timesheet_create_view,
)

app_name = "core"

urlpatterns = [
    # Rotas de navegação Web
    path("", home_redirect_view, name="home"),
    path(
        "login/",
        LoginView.as_view(
            template_name="core/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("analytics/", analytics_view, name="analytics"),
    path("analytics/report/", analytics_report_view, name="analytics_report"),
    path("projects/", projects_view, name="projects"),
    path("projects/create/", project_create_view, name="project_create"),
    path("projects/<int:project_id>/archive/", project_archive_view, name="project_archive"),
    path("projects/<int:project_id>/restore/", project_restore_view, name="project_restore"),
    path("projects/update/", project_update_view, name="project_update"),
    path("tasks/create/", task_create_view, name="task_create"),
    path("tasks/<int:task_id>/archive/", task_archive_view, name="task_archive"),
    path("tasks/<int:task_id>/restore/", task_restore_view, name="task_restore"),
    path("tasks/update/", task_update_view, name="task_update"),
    path("talent-bank/", talent_bank_view, name="talent_bank"),
    path("timesheet/", timesheet_create_view, name="timesheet"),
    path("tasks/<int:task_id>/request-completion/", task_request_completion_view, name="task_request_completion"),
    path("tasks/<int:task_id>/validate-completion/", task_validate_completion_view, name="task_validate_completion"),
    path("tasks/<int:task_id>/reopen/", task_reopen_view, name="task_reopen"),
    path("health/", healthcheck_view, name="healthcheck"),

    # Endpoints REST API (JSON) - Projeto Integrador II
    path("api/v1/timesheet/", api_timesheet_create_view, name="api_timesheet_create"),
    path(
        "api/v1/tasks/<int:task_id>/request-completion/",
        api_task_request_completion_view,
        name="api_task_request_completion",
    ),
    path("api/v1/dashboard/metrics/", api_dashboard_metrics_view, name="api_dashboard_metrics"),
    path("api/v1/analytics/", api_analytics_view, name="api_analytics"),
]
