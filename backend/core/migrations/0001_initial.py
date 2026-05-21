import decimal

import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
                ("username", models.CharField(error_messages={"unique": "A user with that username already exists."}, help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.", max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name="username")),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                ("is_staff", models.BooleanField(default=False, help_text="Designates whether the user can log into this admin site.", verbose_name="staff status")),
                ("is_active", models.BooleanField(default=True, help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.", verbose_name="active")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                ("role", models.CharField(choices=[("ADMIN", "Administrador"), ("MANAGER", "Gerente de Projetos"), ("CONSULTANT", "Consultor Técnico")], default="CONSULTANT", max_length=20)),
                ("hourly_cost", models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ("groups", models.ManyToManyField(blank=True, help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.", related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, help_text="Specific permissions for this user.", related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            options={
                "verbose_name": "Usuário",
                "verbose_name_plural": "Usuários",
                "abstract": False,
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="Contract",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("client_name", models.CharField(max_length=150)),
                ("contract_type", models.CharField(choices=[("RETAINER", "Retainer"), ("FIXED_PRICE", "Preço Fixo"), ("TIME_AND_MATERIALS", "Time and Materials")], max_length=30)),
                ("value", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Contrato",
                "verbose_name_plural": "Contratos",
                "ordering": ("client_name", "start_date"),
            },
        ),
        migrations.CreateModel(
            name="Skill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Skill",
                "verbose_name_plural": "Skills",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="Project",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("budget_allocated", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("contract", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="projects", to="core.contract")),
            ],
            options={
                "verbose_name": "Projeto",
                "verbose_name_plural": "Projetos",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("estimated_hours", models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(0)])),
                ("is_completed", models.BooleanField(default=False)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="assigned_tasks", to="core.user")),
                ("project", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="tasks", to="core.project")),
            ],
            options={
                "verbose_name": "Tarefa",
                "verbose_name_plural": "Tarefas",
                "ordering": ("project__name", "name"),
            },
        ),
        migrations.CreateModel(
            name="Timesheet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("hours_worked", models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(decimal.Decimal("0.01"))])),
                ("is_billable", models.BooleanField(default=True)),
                ("description", models.TextField(blank=True)),
                ("task", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="timesheets", to="core.task")),
                ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="timesheets", to="core.user")),
            ],
            options={
                "verbose_name": "Lançamento de Horas",
                "verbose_name_plural": "Lançamentos de Horas",
                "ordering": ("-date", "task__name"),
            },
        ),
        migrations.CreateModel(
            name="UserSkill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("proficiency", models.CharField(choices=[("BASIC", "Básico"), ("INTERMEDIATE", "Intermediário"), ("ADVANCED", "Avançado"), ("EXPERT", "Especialista")], max_length=20)),
                ("skill", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="user_skills", to="core.skill")),
                ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="user_skills", to="core.user")),
            ],
            options={
                "verbose_name": "Skill do Usuário",
                "verbose_name_plural": "Skills dos Usuários",
                "ordering": ("user__username", "skill__name"),
            },
        ),
        migrations.AddConstraint(
            model_name="project",
            constraint=models.UniqueConstraint(fields=("contract", "name"), name="unique_project_per_contract"),
        ),
        migrations.AddConstraint(
            model_name="userskill",
            constraint=models.UniqueConstraint(fields=("user", "skill"), name="unique_user_skill"),
        ),
    ]
