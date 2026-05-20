from __future__ import annotations

from django import forms

from .models import Contract, Project, Task, Timesheet, User, UserRole


class TimesheetForm(forms.ModelForm):
    """Formulário básico para registrar esforço em tarefas de projeto."""

    class Meta:
        model = Timesheet
        fields = ["user", "task", "date", "hours_worked", "is_billable", "description"]
        labels = {
            "user": "Consultor",
            "task": "Tarefa",
            "date": "Data",
            "hours_worked": "Horas Trabalhadas",
            "is_billable": "Faturável",
            "description": "Descrição técnica",
        }
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Descreva o escopo executado."}),
        }

    def __init__(self, *args, **kwargs) -> None:
        self.current_user: User | None = kwargs.pop("current_user", None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

        if self.current_user is None:
            return

        if self.current_user.role == UserRole.CONSULTANT:
            if self.is_bound:
                self.data = self.data.copy()
                self.data["user"] = str(self.current_user.id)
            self.fields["user"].queryset = User.objects.filter(id=self.current_user.id)
            self.fields["user"].initial = self.current_user.id
            self.fields["user"].required = False
            self.fields["user"].widget = forms.HiddenInput()
            self.fields["task"].queryset = Task.objects.filter(assigned_to=self.current_user).select_related(
                "project"
            )

    def clean(self) -> dict[str, object]:
        cleaned_data = super().clean()

        if self.current_user is None or self.current_user.role != UserRole.CONSULTANT:
            return cleaned_data

        cleaned_data["user"] = self.current_user
        task = cleaned_data.get("task")
        if task is not None and task.assigned_to_id != self.current_user.id:
            self.add_error("task", "Você só pode lançar horas em tarefas atribuídas ao seu usuário.")
        return cleaned_data

    def save(self, commit: bool = True) -> Timesheet:
        instance: Timesheet = super().save(commit=False)
        if self.current_user is not None and self.current_user.role == UserRole.CONSULTANT:
            instance.user = self.current_user
        if commit:
            instance.save()
        return instance


class ProjectManagementForm(forms.ModelForm):
    """Formulário usado por gestão para criar novos projetos operacionais."""

    class Meta:
        model = Project
        fields = ["contract", "manager", "name", "budget_allocated"]
        labels = {
            "contract": "Contrato",
            "manager": "Gerente responsável",
            "name": "Nome do projeto",
            "budget_allocated": "Orçamento alocado",
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["contract"].queryset = Contract.objects.filter(is_active=True).order_by("client_name", "start_date")
        self.fields["manager"].queryset = User.objects.filter(role=UserRole.MANAGER, is_active=True).order_by(
            "first_name", "username"
        )
        self.fields["manager"].required = False
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class TaskManagementForm(forms.ModelForm):
    """Formulário usado por gestão para criar tarefas e atribuir responsáveis."""

    class Meta:
        model = Task
        fields = ["project", "name", "estimated_hours", "assigned_to"]
        labels = {
            "project": "Projeto",
            "name": "Nome da tarefa",
            "estimated_hours": "Horas estimadas",
            "assigned_to": "Responsável",
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.select_related("contract").filter(
            contract__is_active=True,
            is_archived=False,
        )
        self.fields["assigned_to"].queryset = User.objects.filter(role=UserRole.CONSULTANT, is_active=True).order_by(
            "first_name", "username"
        )
        self.fields["assigned_to"].required = False
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class ProjectUpdateForm(forms.Form):
    """Formulário usado por gestão para ajustar dados centrais de um projeto."""

    project = forms.ModelChoiceField(
        queryset=Project.objects.none(),
        label="Projeto",
    )
    manager = forms.ModelChoiceField(queryset=User.objects.none(), label="Gerente responsável", required=False)
    name = forms.CharField(label="Nome do projeto", max_length=150)
    budget_allocated = forms.DecimalField(label="Orçamento alocado", max_digits=12, decimal_places=2)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = Project.objects.select_related("contract").filter(
            contract__is_active=True,
            is_archived=False,
        )
        self.fields["manager"].queryset = User.objects.filter(role=UserRole.MANAGER, is_active=True).order_by(
            "first_name", "username"
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def save(self) -> Project:
        project: Project = self.cleaned_data["project"]
        project.manager = self.cleaned_data["manager"]
        project.name = self.cleaned_data["name"]
        project.budget_allocated = self.cleaned_data["budget_allocated"]
        project.save(update_fields=("manager", "name", "budget_allocated"))
        return project


class TaskUpdateForm(forms.Form):
    """Formulário usado por gestão para replanejar tarefas existentes."""

    task = forms.ModelChoiceField(
        queryset=Task.objects.none(),
        label="Tarefa",
    )
    estimated_hours = forms.DecimalField(label="Horas estimadas", max_digits=8, decimal_places=2)
    assigned_to = forms.ModelChoiceField(queryset=User.objects.none(), label="Responsável", required=False)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["task"].queryset = Task.objects.select_related("project", "project__contract").filter(
            is_archived=False,
            project__is_archived=False,
        )
        self.fields["assigned_to"].queryset = User.objects.filter(role=UserRole.CONSULTANT, is_active=True).order_by(
            "first_name", "username"
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def save(self) -> Task:
        task: Task = self.cleaned_data["task"]
        task.estimated_hours = self.cleaned_data["estimated_hours"]
        task.assigned_to = self.cleaned_data["assigned_to"]
        task.save(update_fields=("estimated_hours", "assigned_to"))
        return task
