"""Testes automatizados para a camada de APIs REST (JSON) e acessibilidade do PI 2."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from core.models import Task, Timesheet, User, UserRole
from tests.helpers import create_project_scenario


class ApiTimesheetTests(TestCase):
    """Valida o endpoint assíncrono de criação de lançamentos de horas."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.scenario = create_project_scenario(username="consultor.api")
        cls.user = cls.scenario["user"]
        cls.task = cls.scenario["task"]

    def test_api_timesheet_requires_authentication(self) -> None:
        response = self.client.post(
            reverse("core:api_timesheet_create"),
            data={"hours_worked": "4.00"},
            content_type="application/json",
        )
        # LoginRequiredDecorator redireciona usuários não autenticados
        self.assertEqual(response.status_code, 302)

    def test_api_timesheet_create_success_with_json_payload(self) -> None:
        self.client.force_login(self.user)
        payload = {
            "task": self.task.id,
            "date": "2026-11-04",
            "hours_worked": "5.50",
            "is_billable": True,
            "description": "Desenvolvimento assíncrono da API REST",
        }

        response = self.client.post(
            reverse("core:api_timesheet_create"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("entry", data)
        self.assertEqual(data["entry"]["hours_worked"], "5,50")
        self.assertEqual(data["entry"]["task"], self.task.name)

        # Valida persistência no banco de dados
        self.assertTrue(Timesheet.objects.filter(description="Desenvolvimento assíncrono da API REST").exists())

    def test_api_timesheet_create_success_with_form_data(self) -> None:
        self.client.force_login(self.user)
        data = {
            "task": self.task.id,
            "date": "2026-11-04",
            "hours_worked": "3.00",
            "is_billable": True,
            "description": "Lançamento via FormData assíncrono",
        }

        response = self.client.post(
            reverse("core:api_timesheet_create"),
            data=data,
        )

        self.assertEqual(response.status_code, 201)
        res_json = response.json()
        self.assertTrue(res_json["success"])
        self.assertEqual(res_json["entry"]["hours_worked"], "3,00")

    def test_api_timesheet_validation_error_returns_400(self) -> None:
        self.client.force_login(self.user)
        # Horas zeradas ou inválidas
        payload = {
            "task": self.task.id,
            "date": "2026-11-04",
            "hours_worked": "0.00",
            "description": "",
        }

        response = self.client.post(
            reverse("core:api_timesheet_create"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("errors", data)
        self.assertIn("hours_worked", data["errors"])


class ApiWorkflowAndMetricsTests(TestCase):
    """Valida endpoints de transição de workflow e métricas analíticas."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.scenario = create_project_scenario(username="consultor.workflow")
        cls.user = cls.scenario["user"]
        cls.task = cls.scenario["task"]

        cls.other_user = User.objects.create_user(
            username="outro.consultor",
            password="pwd",
            role=UserRole.CONSULTANT,
        )

    def test_consultant_can_request_task_completion_via_api(self) -> None:
        self.client.force_login(self.user)
        url = reverse("core:api_task_request_completion", kwargs={"task_id": self.task.id})

        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["task"]["workflow_state"], "in_validation")

        self.task.refresh_from_db()
        self.assertIsNotNone(self.task.completion_requested_at)

    def test_consultant_cannot_request_completion_for_others_task(self) -> None:
        self.client.force_login(self.other_user)
        url = reverse("core:api_task_request_completion", kwargs={"task_id": self.task.id})

        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_dashboard_metrics_api_returns_kpis(self) -> None:
        self.client.force_login(self.user)
        url = reverse("core:api_dashboard_metrics")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("metrics", data)
        self.assertIn("billability_rate", data["metrics"])
        self.assertIn("active_projects_count", data["metrics"])
        self.assertIn("charts", data)
        self.assertIn("billability", data["charts"])
        self.assertIn("projects_burn_rate", data["charts"])
        self.assertIn("billable_percent", data["charts"]["billability"])
        self.assertIn("burn_rates", data["charts"]["projects_burn_rate"])


class AccessibilityTemplateTests(TestCase):
    """Valida presença dos atributos e diretrizes de acessibilidade WCAG 2.1."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.scenario = create_project_scenario(username="user.a11y")
        cls.user = cls.scenario["user"]

    def test_base_template_contains_skip_link_and_landmarks(self) -> None:
        self.client.force_login(self.user)
        response = self.client.get(reverse("core:dashboard"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        # Skip Navigation (WCAG 2.4.1)
        self.assertIn('class="skip-link"', content)
        self.assertIn('href="#main-content"', content)
        self.assertIn('id="main-content"', content)

        # Região Viva e Announcer (WCAG 4.1.3)
        self.assertIn('id="live-announcer"', content)
        self.assertIn('aria-live="polite"', content)

        # Scripts assíncronos
        self.assertIn('/static/js/api.js', content)
