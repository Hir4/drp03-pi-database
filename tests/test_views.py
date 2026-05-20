"""Testes das rotas principais do MVP, incluindo autenticação."""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from core.models import Project, Task, Timesheet, User, UserRole
from tests.helpers import create_project_scenario, create_timesheet


class DashboardAndHealthViewTests(TestCase):
    """Valida disponibilidade das rotas principais e redirecionamentos."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.scenario = create_project_scenario()
        create_timesheet(
            user=cls.scenario["user"],
            task=cls.scenario["task"],
            work_date=date(2026, 4, 1),
            hours_worked=Decimal("2.00"),
            is_billable=True,
        )

    def test_dashboard_page_renders_successfully(self) -> None:
        self.client.force_login(self.scenario["user"])
        response = self.client.get(reverse("core:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/index.html")
        self.assertIn("summary", response.context)
        self.assertEqual(response.context["summary"]["active_projects"], 1)

    def test_home_redirects_to_login_when_user_is_anonymous(self) -> None:
        response = self.client.get(reverse("core:home"))

        self.assertRedirects(response, reverse("core:login"))

    def test_home_redirects_to_dashboard_when_user_is_authenticated(self) -> None:
        self.client.force_login(self.scenario["user"])

        response = self.client.get(reverse("core:home"))

        self.assertRedirects(response, reverse("core:dashboard"))

    def test_login_page_renders_successfully(self) -> None:
        response = self.client.get(reverse("core:login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/login.html")


class ManagementFrontendTests(TestCase):
    """Valida páginas visuais reservadas a gerência e administração."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.manager = User.objects.create_user(
            username="gerente.front",
            password="senha123",
            role=UserRole.MANAGER,
        )
        cls.other_manager = User.objects.create_user(
            username="gerente.segundo",
            password="senha123",
            role=UserRole.MANAGER,
        )
        cls.consultant_scenario = create_project_scenario(username="consultor.front", manager=cls.manager)
        cls.second_consultant = User.objects.create_user(
            username="consultor.segundo",
            password="senha123",
            role=UserRole.CONSULTANT,
        )
        cls.second_contract_scenario = create_project_scenario(
            username="consultor.segundo.cenario",
            manager=cls.other_manager,
        )
        cls.second_contract_scenario["task"].assigned_to = cls.second_consultant
        cls.second_contract_scenario["task"].save(update_fields=("assigned_to",))

    def test_manager_can_open_projects_page(self) -> None:
        self.client.force_login(self.manager)

        response = self.client.get(reverse("core:projects"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/projects.html")

    def test_manager_can_open_talent_bank_page(self) -> None:
        self.client.force_login(self.manager)

        response = self.client.get(reverse("core:talent_bank"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/talent_bank.html")

    def test_manager_can_create_project_from_management_area(self) -> None:
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("core:project_create"),
            data={
                "contract": self.consultant_scenario["contract"].id,
                "manager": self.manager.id,
                "name": "Novo Projeto Gerencial",
                "budget_allocated": "15000.00",
                "next": reverse("core:projects"),
            },
        )

        self.assertRedirects(response, reverse("core:projects"))
        created_project = Project.objects.get(name="Novo Projeto Gerencial")
        self.assertEqual(created_project.manager, self.manager)

    def test_manager_can_create_task_and_assign_consultant(self) -> None:
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("core:task_create"),
            data={
                "project": self.consultant_scenario["project"].id,
                "name": "Nova Tarefa Gerencial",
                "estimated_hours": "24.00",
                "assigned_to": self.consultant_scenario["user"].id,
                "next": reverse("core:projects"),
            },
        )

        self.assertRedirects(response, reverse("core:projects"))
        task = Task.objects.get(name="Nova Tarefa Gerencial")
        self.assertEqual(task.assigned_to, self.consultant_scenario["user"])

    def test_manager_can_update_project_budget_and_name(self) -> None:
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("core:project_update"),
            data={
                "project": self.consultant_scenario["project"].id,
                "manager": self.other_manager.id,
                "name": "Projeto Replanejado",
                "budget_allocated": "3200.00",
                "next": reverse("core:projects"),
            },
        )

        self.assertRedirects(response, reverse("core:projects"))
        project = Project.objects.get(id=self.consultant_scenario["project"].id)
        self.assertEqual(project.name, "Projeto Replanejado")
        self.assertEqual(project.budget_allocated, Decimal("3200.00"))
        self.assertEqual(project.manager, self.other_manager)

    def test_manager_can_update_task_estimate_and_assignment(self) -> None:
        self.client.force_login(self.manager)
        replacement_user = User.objects.create_user(
            username="consultor.substituto",
            password="senha123",
            role=UserRole.CONSULTANT,
        )

        response = self.client.post(
            reverse("core:task_update"),
            data={
                "task": self.consultant_scenario["task"].id,
                "estimated_hours": "72.00",
                "assigned_to": replacement_user.id,
                "next": reverse("core:projects"),
            },
        )

        self.assertRedirects(response, reverse("core:projects"))
        task = Task.objects.get(id=self.consultant_scenario["task"].id)
        self.assertEqual(task.estimated_hours, Decimal("72.00"))
        self.assertEqual(task.assigned_to, replacement_user)

    def test_consultant_cannot_create_project(self) -> None:
        self.client.force_login(self.consultant_scenario["user"])

        response = self.client.post(
            reverse("core:project_create"),
            data={
                "contract": self.consultant_scenario["contract"].id,
                "manager": self.manager.id,
                "name": "Projeto Indevido",
                "budget_allocated": "10000.00",
                "next": reverse("core:projects"),
            },
        )

        self.assertRedirects(response, reverse("core:dashboard"))
        self.assertFalse(Project.objects.filter(name="Projeto Indevido").exists())

    def test_consultant_cannot_create_task(self) -> None:
        self.client.force_login(self.consultant_scenario["user"])

        response = self.client.post(
            reverse("core:task_create"),
            data={
                "project": self.consultant_scenario["project"].id,
                "name": "Tarefa Indevida",
                "estimated_hours": "8.00",
                "assigned_to": self.consultant_scenario["user"].id,
                "next": reverse("core:projects"),
            },
        )

        self.assertRedirects(response, reverse("core:dashboard"))
        self.assertFalse(Task.objects.filter(name="Tarefa Indevida").exists())

    def test_consultant_cannot_update_project(self) -> None:
        self.client.force_login(self.consultant_scenario["user"])

        response = self.client.post(
            reverse("core:project_update"),
            data={
                "project": self.consultant_scenario["project"].id,
                "manager": self.other_manager.id,
                "name": "Projeto Alterado Indevidamente",
                "budget_allocated": "9999.00",
                "next": reverse("core:projects"),
            },
        )

        self.assertRedirects(response, reverse("core:dashboard"))
        project = Project.objects.get(id=self.consultant_scenario["project"].id)
        self.assertNotEqual(project.name, "Projeto Alterado Indevidamente")

    def test_consultant_cannot_update_task(self) -> None:
        self.client.force_login(self.consultant_scenario["user"])

        response = self.client.post(
            reverse("core:task_update"),
            data={
                "task": self.consultant_scenario["task"].id,
                "estimated_hours": "99.00",
                "assigned_to": self.consultant_scenario["user"].id,
                "next": reverse("core:projects"),
            },
        )

        self.assertRedirects(response, reverse("core:dashboard"))
        task = Task.objects.get(id=self.consultant_scenario["task"].id)
        self.assertNotEqual(task.estimated_hours, Decimal("99.00"))

    def test_manager_can_archive_and_restore_project(self) -> None:
        self.client.force_login(self.manager)

        archive_response = self.client.post(
            reverse("core:project_archive", args=[self.consultant_scenario["project"].id]),
            data={"next": reverse("core:projects")},
        )

        self.assertRedirects(archive_response, reverse("core:projects"))
        self.consultant_scenario["project"].refresh_from_db()
        self.assertTrue(self.consultant_scenario["project"].is_archived)

        restore_response = self.client.post(
            reverse("core:project_restore", args=[self.consultant_scenario["project"].id]),
            data={"next": reverse("core:projects")},
        )

        self.assertRedirects(restore_response, reverse("core:projects"))
        self.consultant_scenario["project"].refresh_from_db()
        self.assertFalse(self.consultant_scenario["project"].is_archived)

    def test_manager_can_archive_and_restore_task(self) -> None:
        self.client.force_login(self.manager)

        archive_response = self.client.post(
            reverse("core:task_archive", args=[self.consultant_scenario["task"].id]),
            data={"next": reverse("core:projects")},
        )

        self.assertRedirects(archive_response, reverse("core:projects"))
        self.consultant_scenario["task"].refresh_from_db()
        self.assertTrue(self.consultant_scenario["task"].is_archived)

        restore_response = self.client.post(
            reverse("core:task_restore", args=[self.consultant_scenario["task"].id]),
            data={"next": reverse("core:projects")},
        )

        self.assertRedirects(restore_response, reverse("core:projects"))
        self.consultant_scenario["task"].refresh_from_db()
        self.assertFalse(self.consultant_scenario["task"].is_archived)

    def test_projects_page_filters_by_manager(self) -> None:
        self.client.force_login(self.manager)

        response = self.client.get(reverse("core:projects"), {"manager": str(self.other_manager.id)})

        self.assertEqual(response.status_code, 200)
        project_names = [row["project"].name for row in response.context["projects_overview"]]
        self.assertEqual(project_names, [self.second_contract_scenario["project"].name])

    def test_projects_page_filters_by_consultant(self) -> None:
        self.client.force_login(self.manager)

        response = self.client.get(reverse("core:projects"), {"consultant": str(self.second_consultant.id)})

        self.assertEqual(response.status_code, 200)
        project_names = [row["project"].name for row in response.context["projects_overview"]]
        self.assertEqual(project_names, [self.second_contract_scenario["project"].name])

    def test_projects_page_filters_by_client(self) -> None:
        self.client.force_login(self.manager)

        response = self.client.get(reverse("core:projects"), {"client": str(self.consultant_scenario["contract"].id)})

        self.assertEqual(response.status_code, 200)
        project_names = [row["project"].name for row in response.context["projects_overview"]]
        self.assertEqual(project_names, [self.consultant_scenario["project"].name])

    def test_consultant_is_redirected_from_management_page(self) -> None:
        self.client.force_login(self.consultant_scenario["user"])

        response = self.client.get(reverse("core:projects"))

        self.assertRedirects(response, reverse("core:dashboard"))

    def test_healthcheck_returns_expected_payload(self) -> None:
        response = self.client.get(reverse("core:healthcheck"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "fcn-ti-backend"})


class TimesheetViewTests(TestCase):
    """Valida o formulário de registro de horas e seu fluxo principal."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.scenario = create_project_scenario(username="form.usuario")

    def test_timesheet_page_renders_form_and_recent_entries(self) -> None:
        self.client.force_login(self.scenario["user"])
        response = self.client.get(reverse("core:timesheet"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/timesheet.html")
        self.assertIn("form", response.context)
        self.assertIn("recent_entries", response.context)
        self.assertEqual(list(response.context["form"].fields["user"].queryset), [self.scenario["user"]])
        self.assertEqual(list(response.context["form"].fields["task"].queryset), [self.scenario["task"]])

    def test_timesheet_requires_authentication(self) -> None:
        response = self.client.get(reverse("core:timesheet"))

        self.assertRedirects(response, f"{reverse('core:login')}?next={reverse('core:timesheet')}")

    def test_valid_post_creates_timesheet_and_redirects(self) -> None:
        self.client.force_login(self.scenario["user"])
        response = self.client.post(
            reverse("core:timesheet"),
            data={
                "user": self.scenario["user"].id,
                "task": self.scenario["task"].id,
                "date": "2026-04-10",
                "hours_worked": "4.50",
                "is_billable": "on",
                "description": "Implementação de teste",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("core:timesheet"))
        self.assertEqual(Timesheet.objects.count(), 1)

        created_entry = Timesheet.objects.get()
        self.assertEqual(created_entry.hours_worked, Decimal("4.50"))
        self.assertTrue(created_entry.is_billable)

    def test_invalid_post_keeps_user_on_form(self) -> None:
        self.client.force_login(self.scenario["user"])
        response = self.client.post(
            reverse("core:timesheet"),
            data={
                "user": self.scenario["user"].id,
                "task": self.scenario["task"].id,
                "date": "2026-04-10",
                "hours_worked": "0",
                "description": "Horas inválidas",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Timesheet.objects.count(), 0)
        self.assertTrue(response.context["form"].errors)


class TaskWorkflowViewTests(TestCase):
    """Valida o fluxo de solicitar e aprovar conclusão de tarefas."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.manager = User.objects.create_user(
            username="gestor.workflow",
            password="senha123",
            role=UserRole.MANAGER,
        )
        cls.scenario = create_project_scenario(username="consultor.workflow")
        cls.other_scenario = create_project_scenario(username="consultor.alheio")

    def test_consultant_can_request_completion_for_assigned_task(self) -> None:
        self.client.force_login(self.scenario["user"])

        response = self.client.post(
            reverse("core:task_request_completion", args=[self.scenario["task"].id]),
            data={"next": reverse("core:dashboard")},
        )

        self.assertRedirects(response, reverse("core:dashboard"))
        task = Task.objects.get(id=self.scenario["task"].id)
        self.assertFalse(task.is_completed)
        self.assertEqual(task.completion_requested_by, self.scenario["user"])
        self.assertIsNotNone(task.completion_requested_at)

    def test_consultant_cannot_request_completion_for_other_user_task(self) -> None:
        self.client.force_login(self.scenario["user"])

        response = self.client.post(
            reverse("core:task_request_completion", args=[self.other_scenario["task"].id]),
            data={"next": reverse("core:dashboard")},
        )

        self.assertRedirects(response, reverse("core:dashboard"))
        task = Task.objects.get(id=self.other_scenario["task"].id)
        self.assertIsNone(task.completion_requested_by)
        self.assertIsNone(task.completion_requested_at)
        self.assertFalse(task.is_completed)

    def test_manager_can_validate_requested_task(self) -> None:
        task = Task.objects.get(id=self.scenario["task"].id)
        task.request_completion(requested_by=self.scenario["user"])
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("core:task_validate_completion", args=[task.id]),
            data={"next": reverse("core:projects")},
        )

        self.assertRedirects(response, reverse("core:projects"))
        task.refresh_from_db()
        self.assertTrue(task.is_completed)
        self.assertEqual(task.completion_requested_by, self.scenario["user"])
        self.assertEqual(task.completion_validated_by, self.manager)
        self.assertIsNotNone(task.completion_validated_at)

    def test_manager_can_reopen_task(self) -> None:
        task = Task.objects.get(id=self.scenario["task"].id)
        task.request_completion(requested_by=self.scenario["user"])
        task.validate_completion(validated_by=self.manager)
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("core:task_reopen", args=[task.id]),
            data={"next": reverse("core:projects")},
        )

        self.assertRedirects(response, reverse("core:projects"))
        task.refresh_from_db()
        self.assertFalse(task.is_completed)
        self.assertIsNone(task.completion_requested_by)
        self.assertIsNone(task.completion_requested_at)
        self.assertIsNone(task.completion_validated_by)
        self.assertIsNone(task.completion_validated_at)

    def test_consultant_cannot_post_hours_for_another_user(self) -> None:
        other_scenario = create_project_scenario(username="outro.usuario")
        self.client.force_login(self.scenario["user"])

        response = self.client.post(
            reverse("core:timesheet"),
            data={
                "user": other_scenario["user"].id,
                "task": self.scenario["task"].id,
                "date": "2026-04-11",
                "hours_worked": "2.00",
                "is_billable": "on",
                "description": "Tentativa de spoof de usuário",
            },
        )

        self.assertEqual(response.status_code, 302)
        created_entry = Timesheet.objects.get()
        self.assertEqual(created_entry.user, self.scenario["user"])

    def test_consultant_cannot_post_hours_for_unassigned_task(self) -> None:
        other_scenario = create_project_scenario(username="task.nao.atribuida")
        self.client.force_login(self.scenario["user"])

        response = self.client.post(
            reverse("core:timesheet"),
            data={
                "user": self.scenario["user"].id,
                "task": other_scenario["task"].id,
                "date": "2026-04-11",
                "hours_worked": "2.00",
                "is_billable": "on",
                "description": "Tentativa de usar tarefa não atribuída",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Timesheet.objects.count(), 0)
        self.assertTrue(response.context["form"].errors)