"""Rotas públicas básicas do app principal."""

from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .views import (
    dashboard_view,
    healthcheck_view,
    home_redirect_view,
    project_create_view,
    project_archive_view,
    project_restore_view,
    project_update_view,
    projects_view,
    task_create_view,
    task_archive_view,
    task_request_completion_view,
    task_restore_view,
    task_reopen_view,
    task_update_view,
    task_validate_completion_view,
    talent_bank_view,
    timesheet_create_view,
)

app_name = "core"

urlpatterns = [
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
]
