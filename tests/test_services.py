"""Testes das regras de negócio críticas do dashboard."""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from core.services import (
    calculate_project_billability,
    calculate_project_burn_rate,
    calculate_project_internal_cost,
    calculate_project_profit_margin,
    get_dashboard_context,
)
from tests.helpers import create_project_scenario, create_timesheet


class ProjectMetricsServiceTests(TestCase):
    """Valida os indicadores calculados a partir de lançamentos reais."""

    @classmethod
    def setUpTestData(cls) -> None:
        cls.scenario = create_project_scenario()
        create_timesheet(
            user=cls.scenario["user"],
            task=cls.scenario["task"],
            work_date=date(2026, 4, 1),
            hours_worked=Decimal("5.00"),
            is_billable=True,
        )
        create_timesheet(
            user=cls.scenario["user"],
            task=cls.scenario["task"],
            work_date=date(2026, 4, 2),
            hours_worked=Decimal("3.00"),
            is_billable=False,
        )

    def test_calculates_internal_cost(self) -> None:
        project = self.scenario["project"]
        self.assertEqual(calculate_project_internal_cost(project), Decimal("800.00"))

    def test_calculates_billability(self) -> None:
        project = self.scenario["project"]
        self.assertEqual(calculate_project_billability(project), Decimal("62.50"))

    def test_calculates_burn_rate(self) -> None:
        project = self.scenario["project"]
        self.assertEqual(calculate_project_burn_rate(project), Decimal("40.00"))

    def test_calculates_profit_margin(self) -> None:
        project = self.scenario["project"]
        self.assertEqual(calculate_project_profit_margin(project), Decimal("60.00"))

    def test_builds_dashboard_context_for_active_projects(self) -> None:
        project = self.scenario["project"]

        context = get_dashboard_context()

        self.assertEqual(context["summary"]["active_projects"], 1)
        self.assertEqual(context["summary"]["billability"], Decimal("62.50"))
        self.assertEqual(context["summary"]["burn_rate"], Decimal("40.00"))
        self.assertEqual(context["summary"]["profit_margin"], Decimal("60.00"))
        self.assertEqual(len(context["projects"]), 1)
        self.assertEqual(context["projects"][0]["project"], project)
        self.assertEqual(context["projects"][0]["health"], "Saudável")


class ProjectMetricsEdgeCaseTests(TestCase):
    """Garante comportamento previsível quando ainda não há horas registradas."""

    def test_returns_zeroed_metrics_without_timesheets(self) -> None:
        scenario = create_project_scenario(username="sem.horas")
        project = scenario["project"]

        self.assertEqual(calculate_project_internal_cost(project), Decimal("0.00"))
        self.assertEqual(calculate_project_billability(project), Decimal("0.00"))
        self.assertEqual(calculate_project_burn_rate(project), Decimal("0.00"))
        self.assertEqual(calculate_project_profit_margin(project), Decimal("100.00"))
