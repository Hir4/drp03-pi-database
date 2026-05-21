from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Contract, ContractType, ProficiencyLevel, Project, Skill, Task, Timesheet, User, UserRole, UserSkill

UserMap = dict[str, User]
SkillMap = dict[str, Skill]
ProjectMap = dict[str, Project]
TaskMap = dict[str, Task]


class Command(BaseCommand):
    """Cria uma base previsível de demonstração para o ambiente local."""

    help = "Cria dados iniciais do MVP da FCN TI para desenvolvimento e demonstração."

    def handle(self, *args, **options) -> None:
        users = self._create_users()
        skills = self._create_skills()
        self._link_users_to_skills(users, skills)
        projects = self._create_projects()
        tasks = self._create_tasks(projects, users)
        self._apply_task_workflow_states(tasks, users)
        self._create_timesheets(users, tasks)
        self.stdout.write(
            self.style.SUCCESS(
                "Dados iniciais da FCN TI prontos com portfólio, equipe e histórico expandidos."
            )
        )

    def _create_users(self) -> UserMap:
        """Cria ou atualiza uma equipe de demonstração mais próxima do cenário real."""
        return {
            "admin": self._upsert_user(
                username="admin",
                password="admin123",
                first_name="Admin",
                last_name="FCN",
                email="admin@fcnti.com.br",
                role=UserRole.ADMIN,
                hourly_cost=Decimal("0.00"),
                is_staff=True,
                is_superuser=True,
            ),
            "marina": self._upsert_user(
                username="marina.pm",
                password="manager123",
                first_name="Marina",
                last_name="Souza",
                email="marina@fcnti.com.br",
                role=UserRole.MANAGER,
                hourly_cost=Decimal("120.00"),
                is_staff=True,
            ),
            "rodrigo": self._upsert_user(
                username="rodrigo.ops",
                password="manager123",
                first_name="Rodrigo",
                last_name="Pereira",
                email="rodrigo@fcnti.com.br",
                role=UserRole.MANAGER,
                hourly_cost=Decimal("125.00"),
                is_staff=True,
            ),
            "caio": self._upsert_user(
                username="caio.devops",
                password="consultant123",
                first_name="Caio",
                last_name="Lima",
                email="caio@fcnti.com.br",
                role=UserRole.CONSULTANT,
                hourly_cost=Decimal("95.00"),
            ),
            "julia": self._upsert_user(
                username="julia.data",
                password="consultant123",
                first_name="Julia",
                last_name="Almeida",
                email="julia@fcnti.com.br",
                role=UserRole.CONSULTANT,
                hourly_cost=Decimal("110.00"),
            ),
            "bruno": self._upsert_user(
                username="bruno.backend",
                password="consultant123",
                first_name="Bruno",
                last_name="Ferreira",
                email="bruno@fcnti.com.br",
                role=UserRole.CONSULTANT,
                hourly_cost=Decimal("105.00"),
            ),
            "renata": self._upsert_user(
                username="renata.qa",
                password="consultant123",
                first_name="Renata",
                last_name="Melo",
                email="renata@fcnti.com.br",
                role=UserRole.CONSULTANT,
                hourly_cost=Decimal("88.00"),
            ),
            "larissa": self._upsert_user(
                username="larissa.bi",
                password="consultant123",
                first_name="Larissa",
                last_name="Costa",
                email="larissa@fcnti.com.br",
                role=UserRole.CONSULTANT,
                hourly_cost=Decimal("115.00"),
            ),
            "felipe": self._upsert_user(
                username="felipe.legacy",
                password="consultant123",
                first_name="Felipe",
                last_name="Martins",
                email="felipe@fcnti.com.br",
                role=UserRole.CONSULTANT,
                hourly_cost=Decimal("98.00"),
                is_active=False,
            ),
        }

    def _upsert_user(self, *, username: str, password: str, **defaults) -> User:
        """Mantém o seed idempotente e garante senha atualizada a cada execução."""
        user, _ = User.objects.get_or_create(username=username, defaults=defaults)
        for field_name, field_value in defaults.items():
            setattr(user, field_name, field_value)
        user.set_password(password)
        user.save()
        return user

    def _create_skills(self) -> SkillMap:
        """Cria o catálogo inicial de competências."""
        return {
            "django": self._get_or_create_skill(
                name="Django",
                description="Desenvolvimento backend com Django e boas práticas MVT",
            ),
            "postgresql": self._get_or_create_skill(
                name="PostgreSQL",
                description="Modelagem relacional, administração e performance",
            ),
            "devops": self._get_or_create_skill(
                name="DevOps",
                description="Containerização, automação e infraestrutura",
            ),
            "bi": self._get_or_create_skill(
                name="Business Intelligence",
                description="Construção de indicadores e painéis gerenciais",
            ),
            "react": self._get_or_create_skill(
                name="React",
                description="Desenvolvimento de interfaces web modulares e responsivas",
            ),
            "qa": self._get_or_create_skill(
                name="Quality Assurance",
                description="Planejamento e execução de testes funcionais e regressivos",
            ),
            "data_engineering": self._get_or_create_skill(
                name="Data Engineering",
                description="Pipelines de ingestão, transformação e governança de dados",
            ),
            "security": self._get_or_create_skill(
                name="Cybersecurity",
                description="Práticas de segurança aplicadas à infraestrutura e aplicações",
            ),
        }

    def _get_or_create_skill(self, *, name: str, description: str) -> Skill:
        skill, _ = Skill.objects.update_or_create(name=name, defaults={"description": description})
        return skill

    def _link_users_to_skills(self, users: UserMap, skills: SkillMap) -> None:
        """Relaciona usuários e competências com o nível de proficiência inicial."""
        links: Iterable[tuple[User, Skill, str]] = (
            (users["marina"], skills["django"], ProficiencyLevel.ADVANCED),
            (users["marina"], skills["bi"], ProficiencyLevel.INTERMEDIATE),
            (users["marina"], skills["react"], ProficiencyLevel.BASIC),
            (users["rodrigo"], skills["devops"], ProficiencyLevel.INTERMEDIATE),
            (users["rodrigo"], skills["security"], ProficiencyLevel.INTERMEDIATE),
            (users["caio"], skills["postgresql"], ProficiencyLevel.ADVANCED),
            (users["caio"], skills["devops"], ProficiencyLevel.EXPERT),
            (users["caio"], skills["security"], ProficiencyLevel.INTERMEDIATE),
            (users["julia"], skills["django"], ProficiencyLevel.ADVANCED),
            (users["julia"], skills["bi"], ProficiencyLevel.ADVANCED),
            (users["julia"], skills["data_engineering"], ProficiencyLevel.ADVANCED),
            (users["bruno"], skills["django"], ProficiencyLevel.ADVANCED),
            (users["bruno"], skills["react"], ProficiencyLevel.INTERMEDIATE),
            (users["bruno"], skills["postgresql"], ProficiencyLevel.INTERMEDIATE),
            (users["renata"], skills["qa"], ProficiencyLevel.EXPERT),
            (users["renata"], skills["react"], ProficiencyLevel.BASIC),
            (users["larissa"], skills["bi"], ProficiencyLevel.EXPERT),
            (users["larissa"], skills["data_engineering"], ProficiencyLevel.ADVANCED),
            (users["felipe"], skills["django"], ProficiencyLevel.INTERMEDIATE),
            (users["felipe"], skills["postgresql"], ProficiencyLevel.BASIC),
        )
        for user, skill, proficiency in links:
            UserSkill.objects.update_or_create(
                user=user,
                skill=skill,
                defaults={"proficiency": proficiency},
            )

    def _create_projects(self) -> ProjectMap:
        """Cria contratos e projetos usados no dashboard inicial."""
        atlas = self._upsert_contract(
            client_name="Indústria Atlas",
            contract_type=ContractType.RETAINER,
            value=Decimal("180000.00"),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            is_active=True,
        )
        horizonte = self._upsert_contract(
            client_name="Grupo Horizonte",
            contract_type=ContractType.FIXED_PRICE,
            value=Decimal("95000.00"),
            start_date=date(2026, 2, 15),
            end_date=date(2026, 8, 31),
            is_active=True,
        )
        prisma = self._upsert_contract(
            client_name="Logística Prisma",
            contract_type=ContractType.TIME_AND_MATERIALS,
            value=Decimal("60000.00"),
            start_date=date(2026, 3, 1),
            end_date=None,
            is_active=True,
        )
        aurora = self._upsert_contract(
            client_name="Hospital Aurora",
            contract_type=ContractType.RETAINER,
            value=Decimal("140000.00"),
            start_date=date(2026, 1, 20),
            end_date=date(2026, 11, 30),
            is_active=True,
        )
        varejo = self._upsert_contract(
            client_name="Varejo Nexus",
            contract_type=ContractType.FIXED_PRICE,
            value=Decimal("125000.00"),
            start_date=date(2026, 4, 1),
            end_date=date(2026, 10, 30),
            is_active=True,
        )
        solaris = self._upsert_contract(
            client_name="Operadora Solaris",
            contract_type=ContractType.FIXED_PRICE,
            value=Decimal("48000.00"),
            start_date=date(2025, 9, 1),
            end_date=date(2026, 2, 28),
            is_active=False,
        )

        return {
            "sustentacao_erp": self._get_or_create_project(atlas, "Sustentação ERP", Decimal("70000.00")),
            "modernizacao_dados": self._get_or_create_project(atlas, "Modernização de Dados", Decimal("50000.00")),
            "rollout_sap": self._get_or_create_project(atlas, "Rollout SAP Financeiro", Decimal("5000.00")),
            "portal_cliente": self._get_or_create_project(horizonte, "Portal do Cliente", Decimal("95000.00")),
            "observabilidade": self._get_or_create_project(prisma, "Observabilidade Operacional", Decimal("60000.00")),
            "app_pacientes": self._get_or_create_project(aurora, "App do Paciente", Decimal("80000.00")),
            "analytics_suprimentos": self._get_or_create_project(
                aurora,
                "Analytics de Suprimentos",
                Decimal("60000.00"),
            ),
            "ecommerce_b2b": self._get_or_create_project(varejo, "Portal B2B", Decimal("125000.00")),
            "crm_cancelado": self._get_or_create_project(
                solaris,
                "Implantação CRM Omnichannel",
                Decimal("48000.00"),
            ),
        }

    def _upsert_contract(
        self,
        *,
        client_name: str,
        contract_type: str,
        value: Decimal,
        start_date: date,
        end_date: date | None,
        is_active: bool,
    ) -> Contract:
        contract, _ = Contract.objects.update_or_create(
            client_name=client_name,
            defaults={
                "contract_type": contract_type,
                "value": value,
                "start_date": start_date,
                "end_date": end_date,
                "is_active": is_active,
            },
        )
        return contract

    def _get_or_create_project(self, contract: Contract, name: str, budget_allocated: Decimal) -> Project:
        project, _ = Project.objects.update_or_create(
            contract=contract,
            name=name,
            defaults={
                "budget_allocated": budget_allocated,
                "manager": self._project_manager_for(name),
                "is_archived": False,
            },
        )
        return project

    def _project_manager_for(self, project_name: str) -> User:
        manager_username = "marina.pm"
        if project_name in {"Observabilidade Operacional", "Portal B2B", "Implantação CRM Omnichannel"}:
            manager_username = "rodrigo.ops"
        return User.objects.get(username=manager_username)

    def _create_tasks(self, projects: ProjectMap, users: UserMap) -> TaskMap:
        """Cria as tarefas base que alimentam o registro de horas e os indicadores."""
        return {
            "task_1": self._get_or_create_task(
                project=projects["sustentacao_erp"],
                name="Mapeamento de incidentes críticos",
                estimated_hours=Decimal("40.00"),
                assigned_to=users["marina"],
                is_completed=True,
            ),
            "task_2": self._get_or_create_task(
                project=projects["sustentacao_erp"],
                name="Ajustes de integração fiscal",
                estimated_hours=Decimal("60.00"),
                assigned_to=users["julia"],
                is_completed=False,
            ),
            "task_3": self._get_or_create_task(
                project=projects["modernizacao_dados"],
                name="Pipeline de ingestão para indicadores",
                estimated_hours=Decimal("80.00"),
                assigned_to=users["julia"],
                is_completed=False,
            ),
            "task_3c": self._get_or_create_task(
                project=projects["rollout_sap"],
                name="Saneamento de cadastros críticos do financeiro",
                estimated_hours=Decimal("30.00"),
                assigned_to=users["julia"],
                is_completed=False,
            ),
            "task_3d": self._get_or_create_task(
                project=projects["rollout_sap"],
                name="Parametrização de centros de custo",
                estimated_hours=Decimal("24.00"),
                assigned_to=None,
                is_completed=False,
            ),
            "task_3b": self._get_or_create_task(
                project=projects["modernizacao_dados"],
                name="Modelagem da camada semântica executiva",
                estimated_hours=Decimal("48.00"),
                assigned_to=users["larissa"],
                is_completed=False,
            ),
            "task_4": self._get_or_create_task(
                project=projects["portal_cliente"],
                name="Modelagem de autenticação e perfis",
                estimated_hours=Decimal("120.00"),
                assigned_to=users["bruno"],
                is_completed=False,
            ),
            "task_4b": self._get_or_create_task(
                project=projects["portal_cliente"],
                name="Plano de testes de acesso e jornada crítica",
                estimated_hours=Decimal("32.00"),
                assigned_to=users["renata"],
                is_completed=False,
            ),
            "task_5": self._get_or_create_task(
                project=projects["observabilidade"],
                name="Implantação de logs centralizados",
                estimated_hours=Decimal("90.00"),
                assigned_to=users["caio"],
                is_completed=False,
            ),
            "task_5b": self._get_or_create_task(
                project=projects["observabilidade"],
                name="Hardening de acesso ao cluster de monitoramento",
                estimated_hours=Decimal("36.00"),
                assigned_to=users["caio"],
                is_completed=False,
            ),
            "task_6": self._get_or_create_task(
                project=projects["app_pacientes"],
                name="Protótipo de jornada do paciente autenticado",
                estimated_hours=Decimal("72.00"),
                assigned_to=users["bruno"],
                is_completed=False,
            ),
            "task_6b": self._get_or_create_task(
                project=projects["app_pacientes"],
                name="Integração com agenda de consultas",
                estimated_hours=Decimal("64.00"),
                assigned_to=users["julia"],
                is_completed=False,
            ),
            "task_7": self._get_or_create_task(
                project=projects["analytics_suprimentos"],
                name="Dashboards de ruptura e giro de estoque",
                estimated_hours=Decimal("56.00"),
                assigned_to=users["larissa"],
                is_completed=False,
            ),
            "task_8": self._get_or_create_task(
                project=projects["ecommerce_b2b"],
                name="Catálogo e política comercial por perfil",
                estimated_hours=Decimal("96.00"),
                assigned_to=users["bruno"],
                is_completed=False,
            ),
            "task_8b": self._get_or_create_task(
                project=projects["ecommerce_b2b"],
                name="Plano regressivo para checkout corporativo",
                estimated_hours=Decimal("44.00"),
                assigned_to=users["renata"],
                is_completed=False,
            ),
            "task_9": self._get_or_create_task(
                project=projects["crm_cancelado"],
                name="Migração do histórico de clientes legados",
                estimated_hours=Decimal("52.00"),
                assigned_to=users["felipe"],
                is_completed=False,
            ),
            "task_9b": self._get_or_create_task(
                project=projects["crm_cancelado"],
                name="Mapeamento de integrações do CRM cancelado",
                estimated_hours=Decimal("28.00"),
                assigned_to=users["renata"],
                is_completed=False,
            ),
        }

    def _get_or_create_task(
        self,
        *,
        project: Project,
        name: str,
        estimated_hours: Decimal,
        assigned_to: User | None,
        is_completed: bool,
    ) -> Task:
        task, _ = Task.objects.update_or_create(
            project=project,
            name=name,
            defaults={
                "estimated_hours": estimated_hours,
                "assigned_to": assigned_to,
                "is_completed": is_completed,
            },
        )
        return task

    def _create_timesheets(self, users: UserMap, tasks: TaskMap) -> None:
        """Insere ou atualiza lançamentos de horas para uma linha do tempo mais realista."""
        entries = [
            ("marina", "task_1", date(2026, 4, 1), "6.00", True, "Workshop de priorização com equipe do cliente"),
            ("marina", "task_1", date(2026, 4, 2), "4.50", True, "Fechamento da análise e atualização do backlog"),
            ("julia", "task_2", date(2026, 4, 3), "7.00", True, "Correção de regras fiscais e validação com usuário-chave"),
            ("julia", "task_3", date(2026, 4, 4), "5.50", False, "Pesquisa técnica para arquitetura do pipeline"),
            ("julia", "task_3", date(2026, 4, 5), "6.00", True, "Implementação inicial da ingestão e tratamento de dados"),
            ("julia", "task_3c", date(2026, 4, 10), "8.00", True, "Saneamento inicial de centro de custos e natureza financeira"),
            ("julia", "task_3c", date(2026, 4, 11), "8.00", True, "Correção de cadastros inconsistentes para integração com SAP"),
            ("julia", "task_3c", date(2026, 4, 18), "8.00", True, "Reprocessamento manual após falhas na carga principal"),
            ("julia", "task_3c", date(2026, 4, 20), "8.00", False, "Ajustes emergenciais após divergência no fechamento contábil"),
            ("julia", "task_3c", date(2026, 4, 26), "8.00", True, "Validação com key-user e nova rodada de saneamento"),
            ("julia", "task_3c", date(2026, 5, 3), "8.00", True, "Retrabalho de parametrização após mudança de regra financeira"),
            ("larissa", "task_3b", date(2026, 4, 7), "6.50", True, "Definição de indicadores executivos para diretoria"),
            ("larissa", "task_7", date(2026, 4, 8), "7.00", True, "Construção do dashboard de ruptura por unidade"),
            ("larissa", "task_7", date(2026, 4, 9), "4.00", False, "Refino de taxonomia e validação de dicionário de dados"),
            ("bruno", "task_4", date(2026, 4, 6), "8.00", True, "Implementação inicial de autenticação e perfis"),
            ("renata", "task_4b", date(2026, 4, 7), "5.00", False, "Desenho dos cenários de teste para login e autorização"),
            ("caio", "task_5", date(2026, 4, 7), "7.50", True, "Configuração de stack de observabilidade em container"),
            ("caio", "task_5", date(2026, 4, 8), "3.00", False, "Ajustes internos de ambiente e documentação técnica"),
            ("caio", "task_5b", date(2026, 4, 10), "6.00", True, "Revisão de permissões e credenciais do cluster"),
            ("bruno", "task_6", date(2026, 4, 11), "7.00", True, "Criação do fluxo autenticado do app do paciente"),
            ("julia", "task_6b", date(2026, 4, 12), "6.50", True, "Mapeamento de integração com agenda legada"),
            ("renata", "task_6", date(2026, 4, 14), "4.50", False, "Teste exploratório do onboarding do paciente"),
            ("bruno", "task_8", date(2026, 4, 15), "8.00", True, "Estruturação do catálogo com visões por tipo de cliente"),
            ("renata", "task_8b", date(2026, 4, 16), "6.00", True, "Execução de suíte regressiva no checkout corporativo"),
            ("marina", "task_4", date(2026, 4, 17), "3.50", True, "Alinhamento de escopo e dependências com o cliente"),
            ("rodrigo", "task_5b", date(2026, 4, 18), "2.50", False, "Revisão interna de risco operacional e segurança"),
            ("larissa", "task_7", date(2026, 4, 22), "6.50", True, "Ajuste dos painéis com base no feedback da operação"),
            ("julia", "task_3", date(2026, 4, 23), "7.50", True, "Evolução da carga incremental e tratamento de falhas"),
            ("caio", "task_5", date(2026, 4, 24), "5.50", True, "Automação de coleta de logs por ambiente"),
            ("bruno", "task_8", date(2026, 4, 25), "6.00", True, "Ajustes de política comercial no portal B2B"),
            ("renata", "task_8b", date(2026, 4, 28), "4.00", False, "Consolidação de evidências de regressão"),
            ("larissa", "task_3b", date(2026, 5, 2), "5.00", True, "Validação da camada semântica com time financeiro"),
            ("julia", "task_6b", date(2026, 5, 4), "7.00", True, "Implementação da integração de agenda e retornos"),
            ("caio", "task_5b", date(2026, 5, 5), "4.00", True, "Checklist de hardening e trilhas de auditoria"),
            ("bruno", "task_6", date(2026, 5, 6), "6.50", True, "Refino de componentes para acompanhamento do paciente"),
            ("renata", "task_4b", date(2026, 5, 7), "5.50", True, "Teste regressivo após ajustes de perfil de acesso"),
            ("felipe", "task_9", date(2026, 1, 15), "7.00", True, "Migração inicial da base legada antes da paralisação do projeto"),
            ("felipe", "task_9", date(2026, 1, 22), "6.00", False, "Tentativa de conciliação de clientes duplicados antes do cancelamento"),
        ]

        for username, task_key, entry_date, hours_worked, is_billable, description in entries:
            Timesheet.objects.update_or_create(
                user=users[username],
                task=tasks[task_key],
                date=entry_date,
                defaults={
                    "hours_worked": Decimal(hours_worked),
                    "is_billable": is_billable,
                    "description": description,
                },
            )

    def _apply_task_workflow_states(self, tasks: TaskMap, users: UserMap) -> None:
        """Configura alguns estados operacionais para demonstrar o fluxo de validação."""

        tasks["task_1"].validate_completion(validated_by=users["marina"])
        tasks["task_5"].validate_completion(validated_by=users["rodrigo"])
        tasks["task_4b"].request_completion(requested_by=users["renata"])
        tasks["task_7"].request_completion(requested_by=users["larissa"])
        tasks["task_4b"].completion_requested_at = timezone.make_aware(datetime(2026, 5, 8, 14, 30))
        tasks["task_4b"].save(update_fields=("completion_requested_at",))
        tasks["task_7"].completion_requested_at = timezone.make_aware(datetime(2026, 5, 9, 10, 15))
        tasks["task_7"].save(update_fields=("completion_requested_at",))
        tasks["task_9"].project.archive()
        tasks["task_8b"].archive()
