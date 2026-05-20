"""Modelos centrais do domínio da FCN TI.

Cada classe representa uma entidade de negócio usada no MVP e mantém os nomes
internos em inglês, como exigido na especificação do projeto.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    """Papéis de acesso suportados pela aplicação."""

    ADMIN = "ADMIN", "Administrador"
    MANAGER = "MANAGER", "Gerente de Projetos"
    CONSULTANT = "CONSULTANT", "Consultor Técnico"


class ProficiencyLevel(models.TextChoices):
    """Níveis de proficiência usados para mapear skills dos usuários."""

    BASIC = "BASIC", "Básico"
    INTERMEDIATE = "INTERMEDIATE", "Intermediário"
    ADVANCED = "ADVANCED", "Avançado"
    EXPERT = "EXPERT", "Especialista"


class ContractType(models.TextChoices):
    """Tipos de contrato aceitos para clientes e projetos."""

    RETAINER = "RETAINER", "Retainer"
    FIXED_PRICE = "FIXED_PRICE", "Preço Fixo"
    TIME_AND_MATERIALS = "TIME_AND_MATERIALS", "Time and Materials"


class User(AbstractUser):
    """Usuário do sistema com papel funcional e custo horário interno."""

    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CONSULTANT)
    hourly_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"

    def __str__(self) -> str:
        return self.get_full_name() or self.username


class Skill(models.Model):
    """Competência técnica ou de negócio disponível no banco de talentos."""

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Skill"
        verbose_name_plural = "Skills"
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class UserSkill(models.Model):
    """Relacionamento entre usuário e skill com nível de proficiência."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="user_skills")
    proficiency = models.CharField(max_length=20, choices=ProficiencyLevel.choices)

    class Meta:
        verbose_name = "Skill do Usuário"
        verbose_name_plural = "Skills dos Usuários"
        constraints = [
            models.UniqueConstraint(fields=("user", "skill"), name="unique_user_skill")
        ]
        ordering = ("user__username", "skill__name")

    def __str__(self) -> str:
        return f"{self.user} - {self.skill} ({self.get_proficiency_display()})"


class Contract(models.Model):
    """Contrato comercial firmado com um cliente da consultoria."""

    client_name = models.CharField(max_length=150)
    contract_type = models.CharField(max_length=30, choices=ContractType.choices)
    value = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        ordering = ("client_name", "start_date")

    def __str__(self) -> str:
        return f"{self.client_name} - {self.get_contract_type_display()}"


class Project(models.Model):
    """Projeto operacional vinculado a um contrato e a um orçamento reservado."""

    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="projects")
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="managed_projects",
    )
    name = models.CharField(max_length=150)
    budget_allocated = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    is_archived = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"
        constraints = [
            models.UniqueConstraint(fields=("contract", "name"), name="unique_project_per_contract")
        ]
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def archive(self) -> None:
        """Arquiva o projeto e retira suas tarefas das listas operacionais."""

        self.is_archived = True
        self.save(update_fields=("is_archived",))
        self.tasks.update(is_archived=True)

    def restore(self) -> None:
        """Reativa o projeto para que volte à operação normal."""

        self.is_archived = False
        self.save(update_fields=("is_archived",))
        self.tasks.update(is_archived=False)


class Task(models.Model):
    """Tarefa de WBS usada para planejamento e apontamento de horas."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    name = models.CharField(max_length=150)
    estimated_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="assigned_tasks",
    )
    completion_requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="requested_completion_tasks",
    )
    completion_requested_at = models.DateTimeField(blank=True, null=True)
    completion_validated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="validated_completion_tasks",
    )
    completion_validated_at = models.DateTimeField(blank=True, null=True)
    is_archived = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Tarefa"
        verbose_name_plural = "Tarefas"
        ordering = ("project__name", "name")

    def __str__(self) -> str:
        return f"{self.project.name} - {self.name}"

    @property
    def status_code(self) -> str:
        """Retorna o estado operacional da tarefa para uso em templates e regras."""

        if self.is_completed:
            return "COMPLETED"
        if self.completion_requested_at is not None:
            return "PENDING_APPROVAL"
        return "IN_PROGRESS"

    @property
    def status_label(self) -> str:
        """Versão amigável do estado operacional da tarefa."""

        return {
            "IN_PROGRESS": "Em andamento",
            "PENDING_APPROVAL": "Aguardando validação",
            "COMPLETED": "Concluída",
        }[self.status_code]

    @property
    def status_css_class(self) -> str:
        """Classe CSS associada ao estado operacional da tarefa."""

        return {
            "IN_PROGRESS": "progress",
            "PENDING_APPROVAL": "pending",
            "COMPLETED": "done",
        }[self.status_code]

    def request_completion(self, *, requested_by: User) -> None:
        """Marca a tarefa como pronta para validação gerencial."""

        self.is_completed = False
        self.completion_requested_by = requested_by
        self.completion_requested_at = timezone.now()
        self.completion_validated_by = None
        self.completion_validated_at = None
        self.save(
            update_fields=(
                "is_completed",
                "completion_requested_by",
                "completion_requested_at",
                "completion_validated_by",
                "completion_validated_at",
            )
        )

    def validate_completion(self, *, validated_by: User) -> None:
        """Confirma a entrega da tarefa após revisão de um perfil de gestão."""

        self.is_completed = True
        if self.completion_requested_at is None:
            self.completion_requested_at = timezone.now()
        if self.completion_requested_by is None:
            self.completion_requested_by = self.assigned_to
        self.completion_validated_by = validated_by
        self.completion_validated_at = timezone.now()
        self.save(
            update_fields=(
                "is_completed",
                "completion_requested_by",
                "completion_requested_at",
                "completion_validated_by",
                "completion_validated_at",
            )
        )

    def reopen(self) -> None:
        """Reabre a tarefa para execução quando a entrega ainda não está pronta."""

        self.is_completed = False
        self.completion_requested_by = None
        self.completion_requested_at = None
        self.completion_validated_by = None
        self.completion_validated_at = None
        self.save(
            update_fields=(
                "is_completed",
                "completion_requested_by",
                "completion_requested_at",
                "completion_validated_by",
                "completion_validated_at",
            )
        )

    def archive(self) -> None:
        """Arquiva a tarefa sem apagar histórico já registrado."""

        self.is_archived = True
        self.save(update_fields=("is_archived",))

    def restore(self) -> None:
        """Reativa a tarefa para planejamento e execução."""

        self.is_archived = False
        self.save(update_fields=("is_archived",))


class Timesheet(models.Model):
    """Registro diário de esforço executado por um consultor em uma tarefa."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="timesheets")
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="timesheets")
    date = models.DateField()
    hours_worked = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    is_billable = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Lançamento de Horas"
        verbose_name_plural = "Lançamentos de Horas"
        ordering = ("-date", "task__name")

    def __str__(self) -> str:
        return f"{self.user} - {self.task} - {self.hours_worked}h"
