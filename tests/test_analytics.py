"""Testes da análise gerencial: cálculos, filtros, API, páginas e permissões."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.analytics import (
    AnalyticsFilters,
    build_analytics_payload,
    client_profitability,
    estimate_vs_actual,
    hours_trend,
    parse_analytics_filters,
    project_risk,
    team_load,
    validation_metrics,
)
from core.models import Task, User, UserRole
from tests.helpers import create_project_scenario, create_timesheet


def _aware(year: int, month: int, day: int, hour: int = 10) -> datetime:
    return timezone.make_aware(datetime(year, month, day, hour, 0))


class AnalyticsScenarioMixin:
    """Carteira com dois projetos de perfis opostos.

    - Projeto Alpha (gerente próprio): orçamento R$ 1.000, 9h a R$ 100/h = R$ 900
      de custo (90% do orçamento) e nenhuma das 2 tarefas concluída -> em risco.
    - Projeto Beta: orçamento R$ 4.000, 8h a R$ 50/h = R$ 400 (10%), tarefa
      concluída (100%) e estimativa de 5h estourada (8h realizadas).
    """

    @classmethod
    def setUpTestData(cls) -> None:
        cls.manager = User.objects.create_user(username="gerente.analytics", password="pwd", role=UserRole.MANAGER)
        cls.alpha = create_project_scenario(
            username="consultor.alpha",
            hourly_cost=Decimal("100.00"),
            budget_allocated=Decimal("1000.00"),
            manager=cls.manager,
        )
        cls.beta = create_project_scenario(
            username="consultor.beta",
            hourly_cost=Decimal("50.00"),
            budget_allocated=Decimal("4000.00"),
        )
        cls.alpha_pending_task = Task.objects.create(
            project=cls.alpha["project"],
            name="Tarefa aguardando validação",
            estimated_hours=Decimal("10.00"),
            assigned_to=cls.alpha["user"],
        )

        alpha_user, alpha_task = cls.alpha["user"], cls.alpha["task"]
        create_timesheet(user=alpha_user, task=alpha_task, work_date=date(2026, 4, 6), hours_worked=Decimal("4.00"), is_billable=True)
        create_timesheet(user=alpha_user, task=alpha_task, work_date=date(2026, 4, 8), hours_worked=Decimal("2.00"), is_billable=False)
        create_timesheet(user=alpha_user, task=alpha_task, work_date=date(2026, 4, 20), hours_worked=Decimal("3.00"), is_billable=True)
        create_timesheet(
            user=cls.beta["user"],
            task=cls.beta["task"],
            work_date=date(2026, 4, 7),
            hours_worked=Decimal("8.00"),
            is_billable=True,
        )

        Task.objects.filter(pk=cls.beta["task"].pk).update(
            estimated_hours=Decimal("5.00"),
            is_completed=True,
            completion_requested_at=_aware(2026, 4, 10),
            completion_validated_at=_aware(2026, 4, 12),
        )
        Task.objects.filter(pk=cls.alpha_pending_task.pk).update(
            completion_requested_at=timezone.now() - timedelta(days=3),
        )


class AnalyticsFilterParsingTests(TestCase):
    def test_invalid_values_are_ignored(self) -> None:
        filters = parse_analytics_filters({"start": "ontem", "end": "2026-13-40", "client": "abc", "manager": "-2"})
        self.assertEqual(filters, AnalyticsFilters())

    def test_swapped_dates_are_corrected(self) -> None:
        filters = parse_analytics_filters({"start": "2026-05-01", "end": "2026-04-01"})
        self.assertEqual(filters.start, date(2026, 4, 1))
        self.assertEqual(filters.end, date(2026, 5, 1))

    def test_query_params_only_include_active_filters(self) -> None:
        filters = AnalyticsFilters(start=date(2026, 4, 1), client_id=7)
        self.assertEqual(filters.as_query_params(), {"start": "2026-04-01", "client": "7"})


class AnalyticsCalculationTests(AnalyticsScenarioMixin, TestCase):
    def test_hours_trend_groups_by_week_and_fills_empty_weeks(self) -> None:
        trend = hours_trend(AnalyticsFilters(start=date(2026, 4, 6), end=date(2026, 4, 26)))

        self.assertEqual(trend["granularity"], "week")
        self.assertEqual(trend["labels"], ["06/04", "13/04", "20/04"])
        self.assertEqual(trend["billable_hours"], [12.0, 0.0, 3.0])
        self.assertEqual(trend["non_billable_hours"], [2.0, 0.0, 0.0])
        self.assertEqual(trend["billability"][0], 85.71)
        self.assertEqual(len(trend["rows"]), 3)

    def test_hours_trend_uses_months_for_long_periods(self) -> None:
        trend = hours_trend(AnalyticsFilters(start=date(2025, 1, 1), end=date(2026, 12, 31)))

        self.assertEqual(trend["granularity"], "month")
        self.assertEqual(trend["labels"][0], "jan/2025")
        self.assertEqual(len(trend["labels"]), 24)
        self.assertEqual(trend["billable_hours"][trend["labels"].index("abr/2026")], 15.0)

    def test_hours_trend_without_dates_uses_data_range(self) -> None:
        trend = hours_trend(AnalyticsFilters())
        self.assertEqual(trend["labels"], ["06/04", "13/04", "20/04"])

    def test_client_filter_limits_trend_to_its_projects(self) -> None:
        trend = hours_trend(AnalyticsFilters(client_id=self.alpha["contract"].id))
        self.assertEqual(trend["billable_hours"], [4.0, 0.0, 3.0])

    def test_estimate_vs_actual_flags_overrun_first(self) -> None:
        rows = estimate_vs_actual(AnalyticsFilters())

        self.assertEqual(rows[0]["project"], self.beta["project"].name)
        self.assertEqual(rows[0]["estimated_hours"], 5.0)
        self.assertEqual(rows[0]["actual_hours"], 8.0)
        self.assertEqual(rows[0]["variance_percent"], 60.0)
        self.assertEqual(rows[0]["status"], "Acima da estimativa")
        self.assertEqual(rows[1]["estimated_hours"], 50.0)
        self.assertEqual(rows[1]["status"], "Dentro da estimativa")

    def test_project_risk_compares_budget_with_progress(self) -> None:
        rows = project_risk(AnalyticsFilters())
        by_project = {row["project"]: row for row in rows}

        alpha = by_project[self.alpha["project"].name]
        self.assertEqual(alpha["burn_rate"], 90.0)
        self.assertEqual(alpha["progress"], 0.0)
        self.assertEqual(alpha["risk_level"], "high")
        self.assertEqual(alpha["manager"], "gerente.analytics")

        beta = by_project[self.beta["project"].name]
        self.assertEqual(beta["burn_rate"], 10.0)
        self.assertEqual(beta["progress"], 100.0)
        self.assertEqual(beta["risk_level"], "ok")
        self.assertEqual(rows[0]["project"], self.alpha["project"].name)

    def test_manager_filter_keeps_only_their_projects(self) -> None:
        rows = project_risk(AnalyticsFilters(manager_id=self.manager.id))
        self.assertEqual([row["project"] for row in rows], [self.alpha["project"].name])

    def test_team_load_respects_period(self) -> None:
        rows = team_load(AnalyticsFilters(start=date(2026, 4, 13)))
        by_name = {row["name"]: row for row in rows}

        self.assertEqual(by_name["consultor.alpha"]["total_hours"], 3.0)
        self.assertEqual(by_name["consultor.beta"]["total_hours"], 0.0)

    def test_team_load_billability_per_person(self) -> None:
        rows = team_load(AnalyticsFilters())
        alpha = next(row for row in rows if row["name"] == "consultor.alpha")
        self.assertEqual(alpha["total_hours"], 9.0)
        self.assertEqual(alpha["billable_hours"], 7.0)
        self.assertEqual(alpha["billability"], 77.78)

    def test_client_profitability_lists_lowest_margin_first(self) -> None:
        rows = client_profitability(AnalyticsFilters())

        self.assertEqual(rows[0]["client"], self.alpha["contract"].client_name)
        self.assertEqual(rows[0]["budget"], 1000.0)
        self.assertEqual(rows[0]["internal_cost"], 900.0)
        self.assertEqual(rows[0]["margin_percent"], 10.0)
        self.assertEqual(rows[1]["margin_percent"], 90.0)

    def test_validation_metrics_average_and_pending_queue(self) -> None:
        metrics = validation_metrics(AnalyticsFilters())

        self.assertEqual(metrics["validated_count"], 1)
        self.assertEqual(metrics["average_lead_time_days"], 2.0)
        self.assertEqual(metrics["average_lead_time_hours"], 48.0)
        self.assertEqual(metrics["pending_count"], 1)
        self.assertEqual(metrics["pending"][0]["task"], "Tarefa aguardando validação")
        self.assertAlmostEqual(metrics["oldest_pending_days"], 3.0, delta=0.1)

    def test_direct_completion_is_left_out_of_average(self) -> None:
        self.alpha["task"].validate_completion(validated_by=self.manager)
        metrics = validation_metrics(AnalyticsFilters())

        self.assertEqual(metrics["validated_count"], 1)
        self.assertEqual(metrics["average_lead_time_days"], 2.0)

    def test_validation_metrics_respect_period(self) -> None:
        metrics = validation_metrics(AnalyticsFilters(end=date(2026, 4, 11)))
        self.assertEqual(metrics["validated_count"], 0)
        self.assertIsNone(metrics["average_lead_time_days"])

    def test_payload_kpis_summarize_period(self) -> None:
        payload = build_analytics_payload(AnalyticsFilters(start=date(2026, 4, 6), end=date(2026, 4, 26)))
        kpis = payload["kpis"]

        self.assertEqual(kpis["total_hours"], 17.0)
        self.assertEqual(kpis["billable_hours"], 15.0)
        self.assertEqual(kpis["internal_cost"], 1300.0)
        self.assertEqual(kpis["projects_at_risk"], 1)
        self.assertEqual(kpis["active_projects"], 2)
        self.assertEqual(payload["filters"]["period"], "06/04/2026 a 26/04/2026")


class AnalyticsApiTests(AnalyticsScenarioMixin, TestCase):
    def test_requires_authentication(self) -> None:
        response = self.client.get(reverse("core:api_analytics"))
        self.assertEqual(response.status_code, 302)

    def test_consultant_is_forbidden(self) -> None:
        self.client.force_login(self.alpha["user"])
        response = self.client.get(reverse("core:api_analytics"))

        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()["success"])

    def test_manager_receives_all_blocks_with_filters(self) -> None:
        self.client.force_login(self.manager)
        response = self.client.get(reverse("core:api_analytics"), {"start": "2026-04-06", "end": "2026-04-26"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        for key in ("kpis", "hours_trend", "estimate_vs_actual", "project_risk", "team_load", "client_profitability", "validation"):
            self.assertIn(key, data)
        self.assertEqual(data["filters"]["start"], "2026-04-06")
        self.assertEqual(data["hours_trend"]["labels"], ["06/04", "13/04", "20/04"])

    def test_rejects_post(self) -> None:
        self.client.force_login(self.manager)
        response = self.client.post(reverse("core:api_analytics"))
        self.assertEqual(response.status_code, 405)


class AnalyticsPageTests(AnalyticsScenarioMixin, TestCase):
    def test_manager_sees_charts_tables_and_export_link(self) -> None:
        self.client.force_login(self.manager)
        response = self.client.get(reverse("core:analytics"), {"start": "2026-04-06"})

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        for canvas_id in ("chart-hours-trend", "chart-project-risk", "chart-estimate-actual", "chart-team-load", "chart-client-profit"):
            self.assertIn(f'id="{canvas_id}"', content)
        self.assertIn("Ver dados em tabela", content)
        self.assertIn("/analytics/report/?start=2026-04-06&amp;autoprint=1", content)
        self.assertIn('data-api-url="/api/v1/analytics/?start=2026-04-06"', content)
        self.assertIn(self.alpha["project"].name, content)

    def test_consultant_is_redirected_to_dashboard(self) -> None:
        self.client.force_login(self.alpha["user"])
        response = self.client.get(reverse("core:analytics"))
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_report_page_is_print_ready(self) -> None:
        self.client.force_login(self.manager)
        response = self.client.get(reverse("core:analytics_report"), {"client": self.alpha["contract"].id, "autoprint": "1"})

        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Relatório de Análise Gerencial", content)
        self.assertIn('data-autoprint="1"', content)
        self.assertIn('id="report-print-button"', content)
        self.assertIn(self.alpha["contract"].client_name, content)
        self.assertNotIn("Ver dados em tabela", content)

    def test_consultant_cannot_open_report(self) -> None:
        self.client.force_login(self.alpha["user"])
        response = self.client.get(reverse("core:analytics_report"))
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_navigation_shows_analytics_only_for_management(self) -> None:
        analytics_link = f'href="{reverse("core:analytics")}"'

        self.client.force_login(self.manager)
        self.assertIn(analytics_link, self.client.get(reverse("core:dashboard")).content.decode("utf-8"))

        self.client.force_login(self.alpha["user"])
        self.assertNotIn(analytics_link, self.client.get(reverse("core:dashboard")).content.decode("utf-8"))
