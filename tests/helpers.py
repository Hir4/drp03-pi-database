"""Helpers simples para montar cenários de teste legíveis e reutilizáveis."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from core.models import Contract, ContractType, Project, Task, Timesheet, User, UserRole


def create_project_scenario(
    *,
    username: str = "consultor.teste",
    hourly_cost: Decimal = Decimal("100.00"),
    budget_allocated: Decimal = Decimal("2000.00"),
    contract_active: bool = True,
    manager: User | None = None,
) -> dict[str, object]:
    """Cria um cenário mínimo de projeto com usuário, contrato, projeto e tarefa."""
    user = User.objects.create_user(
        username=username,
        password="senha-teste",
        role=UserRole.CONSULTANT,
        hourly_cost=hourly_cost,
    )
    contract = Contract.objects.create(
        client_name=f"Cliente {username}",
        contract_type=ContractType.FIXED_PRICE,
        value=budget_allocated,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        is_active=contract_active,
    )
    project = Project.objects.create(
        contract=contract,
        manager=manager,
        name=f"Projeto {username}",
        budget_allocated=budget_allocated,
    )
    task = Task.objects.create(
        project=project,
        name="Tarefa principal",
        estimated_hours=Decimal("40.00"),
        assigned_to=user,
    )
    return {
        "user": user,
        "contract": contract,
        "project": project,
        "task": task,
    }


def create_timesheet(
    *,
    user: User,
    task: Task,
    work_date: date,
    hours_worked: Decimal,
    is_billable: bool,
    description: str = "Lançamento de teste",
) -> Timesheet:
    """Cria um lançamento de horas explícito e fácil de ler nos testes."""
    return Timesheet.objects.create(
        user=user,
        task=task,
        date=work_date,
        hours_worked=hours_worked,
        is_billable=is_billable,
        description=description,
    )
