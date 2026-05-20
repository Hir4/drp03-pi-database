# FCN TI | Plataforma de Gestão Integrada

Este repositório contém o MVP acadêmico da plataforma da FCN TI, pensado para centralizar dados de operação, projetos, contratos, equipe técnica e lançamentos de horas em um único sistema.

A ideia principal é substituir controles espalhados em planilhas por uma aplicação mais organizada, com dados consistentes, métricas em tempo real e uma base clara para evolução futura.

Hoje o projeto já entrega:

- backend funcional em Django;
- banco PostgreSQL isolado em container próprio;
- autenticação inicial com tela de login;
- dashboard com indicadores de projetos;
- formulário de registro de horas;
- carga automática de dados de demonstração;
- testes automatizados iniciais.

Os mocks já incluem cenários mais próximos da operação real, como ex-funcionário inativo com histórico preservado, projeto crítico por consumo acima do orçamento, projeto cancelado/arquivado e tarefa momentaneamente sem responsável.

## O que este sistema resolve

Na prática, a aplicação foi desenhada para apoiar uma consultoria de TI que precisa:

- controlar usuários e seus papéis dentro da operação;
- registrar competências técnicas da equipe;
- organizar contratos e projetos por cliente;
- quebrar projetos em tarefas;
- registrar horas trabalhadas;
- acompanhar faturamento, consumo de orçamento e margem.

Em vez de tratar essas informações de forma separada, o sistema concentra tudo em um fluxo único.

## Tecnologias utilizadas

O projeto segue a stack definida na especificação:

- Backend: Python 3.11 + Django;
- Banco de dados: PostgreSQL 15;
- Infraestrutura: Docker e Docker Compose;
- Frontend futuro: HTML5 + CSS3 puros.

## Estrutura do repositório

Os diretórios e arquivos principais são:

- [backend](backend): aplicação Django com models, views, serviços, templates, admin, migrações e seed de dados;
- [tests](tests): testes automatizados da aplicação;
- [docker-compose.yml](docker-compose.yml): composição dos serviços `backend` e `db`;
- [.env.example](.env.example): configuração padrão de ambiente local;

## Como o sistema funciona

O ambiente sobe dois serviços separados:

- `db`: container do PostgreSQL, responsável por armazenar os dados;
- `backend`: container do Django, responsável pela aplicação web.

Quando o backend inicia, ele executa automaticamente:

1. as migrações do Django para criar e atualizar a estrutura do banco;
2. o seed com dados de demonstração;
3. o servidor web da aplicação.

Essa abordagem evita conflito entre modelagem, banco e dados de apresentação, porque existe uma única fonte de verdade:

- estrutura do banco: migrações do Django;
- dados mockados: [backend/core/management/commands/seed_demo_data.py](backend/core/management/commands/seed_demo_data.py).

## Fluxo de acesso atual

Agora a rota inicial do sistema faz mais sentido para uso real:

- ao acessar a raiz da aplicação, o usuário é levado para a tela de login;
- depois do login, o sistema redireciona para o dashboard;
- as páginas principais ficam protegidas por autenticação.

Esse comportamento é mais coerente para um sistema interno e já prepara o projeto para evoluir regras de permissão por perfil.

## Perfis de usuário

O sistema trabalha com três papéis principais:

### Administrador

Perfil com maior nível de acesso.

Responsabilidades esperadas:

- administrar usuários;
- administrar contratos, projetos, tarefas e skills;
- acessar o painel administrativo do Django;
- apoiar manutenção e gestão geral do sistema.

No estado atual do MVP, o administrador é o perfil que já tem acesso ao admin do Django.

### Gerente de Projetos

Perfil voltado ao acompanhamento operacional e gerencial.

Responsabilidades esperadas:

- criar projetos dentro dos contratos ativos;
- ajustar nome e orçamento dos projetos em andamento;
- cadastrar tarefas e atribuir responsáveis da equipe técnica;
- replanejar tarefas trocando responsável e horas estimadas;
- filtrar a carteira por cliente, gerente e consultor;
- arquivar e reativar projetos e tarefas sem excluir histórico;
- acompanhar indicadores do dashboard;
- analisar a saúde dos projetos;
- validar entregas sinalizadas pela equipe e reabrir quando necessário;
- acompanhar contratos, tarefas e esforço registrado;
- apoiar decisões sobre orçamento e produtividade.

### Consultor Técnico

Perfil voltado à execução operacional.

Responsabilidades esperadas:

- registrar horas trabalhadas;
- consultar tarefas atribuídas;
- alimentar o sistema com dados que impactam os indicadores.

### Observação importante sobre permissões

Os papéis já existem no modelo de dados e no login, mas a segregação fina de telas e ações por perfil ainda será expandida nas próximas etapas.

Hoje o projeto já possui:

- autenticação obrigatória para acessar o conteúdo principal;
- fluxo operacional de conclusão de tarefas com solicitação do consultor e validação da gestão;
- criação de projeto e tarefa pela própria área de gestão;
- acesso ao admin para usuários com permissão de staff.

## Pré-requisitos

O jeito mais fácil de rodar o projeto localmente é usando Docker.

Você precisa ter instalado:

- Git;
- Docker;
- Docker Compose.

Se estiver usando versões recentes do Docker, o Compose normalmente já vem integrado no comando `docker compose`.

## Instalação de pré-requisitos

### Windows

O caminho mais simples é:

1. instalar o Git for Windows;
2. instalar o Docker Desktop;
3. garantir que o WSL2 esteja habilitado, se o Docker solicitar;
4. reiniciar a máquina, se necessário.

Depois disso, abra:

- PowerShell;
- Prompt de Comando; ou
- terminal do VS Code.

Para validar a instalação, rode:

```powershell
git --version
docker --version
docker compose version
```

### Linux

Em distribuições baseadas em Ubuntu/Debian, o caminho mais comum é:

```bash
sudo apt update
sudo apt install git docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

Depois valide:

```bash
git --version
docker --version
docker compose version
```

Se quiser rodar Docker sem `sudo`, normalmente também é recomendado adicionar seu usuário ao grupo `docker`.

## Como subir o projeto localmente em poucos passos

### Passo 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd drp03-pi-database
```

### Passo 2. Criar o arquivo de ambiente

```bash
cp .env.example .env
```

No Windows, se estiver usando PowerShell, você pode copiar o arquivo manualmente pelo Explorer ou usar:

```powershell
Copy-Item .env.example .env
```

### Passo 3. Subir a aplicação

```bash
docker compose up --build
```

Na primeira execução pode demorar um pouco mais, porque as imagens e dependências precisam ser preparadas.

### Passo 4. Acessar o sistema

Quando tudo terminar de subir, use:

- login da aplicação: http://localhost:8000/
- dashboard: http://localhost:8000/dashboard/
- registro de horas: http://localhost:8000/timesheet/
- admin Django: http://localhost:8000/admin/

## Como parar o projeto

```bash
docker compose down
```

## Como recriar o ambiente do zero

Se quiser apagar o volume do banco e reconstruir tudo:

```bash
docker compose down -v
docker compose up --build
```

Isso é útil quando você quer reiniciar a base com os dados mockados desde o começo.

## Credenciais de desenvolvimento

### Banco PostgreSQL

- banco: `fcn_ti_db`
- usuário: `fcn_admin`
- senha: `fcn_password`

### Usuários de demonstração

- administrador: `admin` / `admin123`
- gerente: `marina.pm` / `manager123`
- gerente: `rodrigo.ops` / `manager123`
- consultor: `caio.devops` / `consultant123`
- consultora: `julia.data` / `consultant123`
- consultor: `bruno.backend` / `consultant123`
- consultora: `renata.qa` / `consultant123`
- consultora: `larissa.bi` / `consultant123`

## Como rodar os testes

O projeto já possui uma suíte inicial de testes cobrindo:

- métricas de negócio do dashboard;
- rotas principais da aplicação;
- fluxo de autenticação inicial.

### Executando com ambiente virtual ativo

Se você estiver com o ambiente virtual ativado, rode:

```bash
python backend/manage.py test tests --settings=config.test_settings
```

### Executando com caminho explícito do Python do ambiente virtual

Se preferir usar o executável diretamente:

```bash
.venv/bin/python backend/manage.py test tests --settings=config.test_settings
```

No Windows, o equivalente costuma ser algo como:

```powershell
.venv\Scripts\python.exe backend\manage.py test tests --settings=config.test_settings
```

## Arquivos mais importantes para entender o projeto

Se você estiver chegando agora, vale começar por estes pontos:

- [backend/core/models.py](backend/core/models.py): entidades principais do domínio;
- [backend/core/services.py](backend/core/services.py): regras de negócio e cálculos analíticos;
- [backend/core/views.py](backend/core/views.py): fluxo de entrada, dashboard e registro de horas;
- [backend/core/urls.py](backend/core/urls.py): rotas principais do app;
- [backend/core/management/commands/seed_demo_data.py](backend/core/management/commands/seed_demo_data.py): dados de demonstração;
- [backend/config/settings.py](backend/config/settings.py): configuração principal da aplicação;
- [backend/config/test_settings.py](backend/config/test_settings.py): configuração de testes.

## Estado atual do MVP

Hoje o projeto já possui:

- backend Django funcional;
- PostgreSQL rodando em container separado;
- autenticação inicial com login como rota padrão;
- dashboard inicial com métricas analíticas;
- formulário de lançamento de horas;
- seed automático de dados de apresentação;
- testes automatizados iniciais.

## Resumo final

Se a sua intenção é apenas subir o projeto sem complicação, o caminho mais simples é:

1. instalar Git + Docker;
2. clonar o repositório;
3. copiar `.env.example` para `.env`;
4. rodar `docker compose up --build`;
5. abrir `http://localhost:8000/` e entrar com um usuário de demonstração.

Esse fluxo já deve ser suficiente para apresentar o software localmente sem dificuldade.
