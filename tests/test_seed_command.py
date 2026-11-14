"""Testes do comando de seed usado no ambiente de demonstração."""

from django.core.management import call_command
from django.db.models import Sum
from django.test import TestCase

from core.analytics import AnalyticsFilters, build_analytics_payload
from core.models import Contract, Project, Skill, Task, Timesheet, User, UserSkill
from core.services import get_projects_overview


class SeedDemoDataCommandTests(TestCase):
    """Garante que o seed gera massa realista e pode ser executado mais de uma vez."""

    def test_seed_command_populates_realistic_demo_dataset_idempotently(self) -> None:
        call_command("seed_demo_data")

        self.assertEqual(User.objects.count(), 12)
        self.assertEqual(Skill.objects.count(), 10)
        self.assertEqual(UserSkill.objects.count(), 30)
        self.assertEqual(Contract.objects.count(), 7)
        self.assertEqual(Project.objects.count(), 10)
        self.assertEqual(Task.objects.count(), 39)
        self.assertEqual(Timesheet.objects.count(), 673)
        self.assertTrue(User.objects.filter(username="rodrigo.ops").exists())
        self.assertTrue(Project.objects.filter(name="Portal B2B").exists())
        self.assertTrue(User.objects.filter(username="felipe.legacy", is_active=False).exists())
        self.assertTrue(Task.objects.filter(name="Parametrização de centros de custo", assigned_to__isnull=True).exists())

        cancelled_project = Project.objects.get(name="Implantação CRM Omnichannel")
        self.assertTrue(cancelled_project.is_archived)
        self.assertFalse(cancelled_project.contract.is_active)
        self.assertEqual(cancelled_project.tasks.filter(is_archived=True).count(), 2)

        critical_project = next(
            row for row in get_projects_overview() if row["project"].name == "Rollout SAP Financeiro"
        )
        self.assertEqual(critical_project["health"], "Crítico")

        # Histórico ampliado: série de janeiro a novembro, sem fins de semana nem dias acima de 8h.
        payload = build_analytics_payload(AnalyticsFilters())
        self.assertEqual(payload["hours_trend"]["labels"][0], "jan/2026")
        self.assertEqual(payload["hours_trend"]["labels"][-1], "nov/2026")
        self.assertFalse(Timesheet.objects.filter(date__week_day__in=[1, 7], date__gt="2026-05-09").exists())
        self.assertLessEqual(
            max(row["h"] for row in Timesheet.objects.values("user", "date").annotate(h=Sum("hours_worked"))),
            8,
        )
        risk = {row["project"]: row["risk_level"] for row in payload["project_risk"]}
        self.assertEqual(risk["App do Paciente"], "high")
        self.assertEqual(risk["Observabilidade Operacional"], "warning")
        self.assertEqual(risk["Portal do Cliente"], "ok")
        self.assertEqual(payload["validation"]["validated_count"], 17)
        self.assertEqual(payload["validation"]["pending_count"], 4)

        call_command("seed_demo_data")

        self.assertEqual(User.objects.count(), 12)
        self.assertEqual(Skill.objects.count(), 10)
        self.assertEqual(UserSkill.objects.count(), 30)
        self.assertEqual(Contract.objects.count(), 7)
        self.assertEqual(Project.objects.count(), 10)
        self.assertEqual(Task.objects.count(), 39)
        self.assertEqual(Timesheet.objects.count(), 673)
