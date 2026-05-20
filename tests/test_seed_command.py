"""Testes do comando de seed usado no ambiente de demonstração."""

from django.core.management import call_command
from django.test import TestCase

from core.models import Contract, Project, Skill, Task, Timesheet, User, UserSkill
from core.services import get_projects_overview


class SeedDemoDataCommandTests(TestCase):
    """Garante que o seed gera massa realista e pode ser executado mais de uma vez."""

    def test_seed_command_populates_realistic_demo_dataset_idempotently(self) -> None:
        call_command("seed_demo_data")

        self.assertEqual(User.objects.count(), 9)
        self.assertEqual(Skill.objects.count(), 8)
        self.assertEqual(UserSkill.objects.count(), 20)
        self.assertEqual(Contract.objects.count(), 6)
        self.assertEqual(Project.objects.count(), 9)
        self.assertEqual(Task.objects.count(), 17)
        self.assertEqual(Timesheet.objects.count(), 38)
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

        call_command("seed_demo_data")

        self.assertEqual(User.objects.count(), 9)
        self.assertEqual(Skill.objects.count(), 8)
        self.assertEqual(UserSkill.objects.count(), 20)
        self.assertEqual(Contract.objects.count(), 6)
        self.assertEqual(Project.objects.count(), 9)
        self.assertEqual(Task.objects.count(), 17)
        self.assertEqual(Timesheet.objects.count(), 38)
