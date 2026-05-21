"""Configuração do Django Admin para as entidades principais do MVP."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Contract, Project, Skill, Task, Timesheet, User, UserSkill


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Exibe o usuário customizado com os campos extras da FCN TI."""

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Informações FCN TI", {"fields": ("role", "hourly_cost")}),
    )
    list_display = ("username", "email", "role", "hourly_cost", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    """Admin enxuto para consulta do catálogo de skills."""

    list_display = ("name",)
    search_fields = ("name",)


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    """Admin do vínculo entre consultores e competências."""

    list_display = ("user", "skill", "proficiency")
    list_filter = ("proficiency",)
    autocomplete_fields = ("user", "skill")


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    """Admin para contratos comerciais e seu ciclo de vida."""

    list_display = ("client_name", "contract_type", "value", "start_date", "end_date", "is_active")
    list_filter = ("contract_type", "is_active")
    search_fields = ("client_name",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin para projetos vinculados aos contratos."""

    list_display = ("name", "contract", "manager", "budget_allocated", "is_archived")
    search_fields = ("name", "contract__client_name")
    list_filter = ("is_archived",)
    autocomplete_fields = ("contract", "manager")


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Admin para tarefas operacionais da WBS."""

    list_display = (
        "name",
        "project",
        "assigned_to",
        "estimated_hours",
        "is_archived",
        "is_completed",
        "completion_requested_at",
        "completion_validated_at",
    )
    list_filter = ("is_archived", "is_completed", "completion_requested_at", "completion_validated_at")
    search_fields = ("name", "project__name")
    autocomplete_fields = (
        "project",
        "assigned_to",
        "completion_requested_by",
        "completion_validated_by",
    )


@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    """Admin para lançamentos de horas usados nos indicadores do dashboard."""

    list_display = ("user", "task", "date", "hours_worked", "is_billable")
    list_filter = ("is_billable", "date")
    search_fields = ("user__username", "task__name", "description")
    autocomplete_fields = ("user", "task")
