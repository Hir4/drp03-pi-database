# drp03-pi-database

Este projeto cria um ambiente simples para simular um banco de dados de uma consultoria de TI.

Ele foi pensado para trabalho acadêmico e demonstra, de forma visual, como:

- um banco PostgreSQL pode ser criado automaticamente;
- tabelas podem ser montadas com SQL;
- dados de exemplo podem ser inseridos automaticamente;
- um dashboard pode ler esses dados e exibir gráficos.

O projeto usa Docker para deixar tudo mais fácil. Isso significa que você não precisa instalar PostgreSQL manualmente no seu computador para testar o banco.

## O que existe neste repositório

### `docker-compose.yml`

Este arquivo liga todos os serviços do projeto.

Ele sobe dois containers:

- `db`: o banco de dados PostgreSQL;
- `dashboard`: a interface visual feita com Streamlit.

### Pasta `database/`

Essa pasta guarda os scripts SQL usados para preparar o banco.

- `01_init.sql`: cria as tabelas;
- `02_mock_data.sql`: insere dados de exemplo.

### Pasta `dashboard/`

Essa pasta guarda a aplicação visual.

- `app.py`: busca os dados no banco e mostra indicadores, tabela e graficos;
- `requirements.txt`: lista as bibliotecas Python usadas;
- `Dockerfile`: define como o container do dashboard sera montado.

## Como o projeto funciona

Quando você executa o comando para subir o projeto, o Docker faz o seguinte:

1. baixa ou usa a imagem do PostgreSQL;
2. cria o banco chamado `consultoria_db`;
3. executa os arquivos SQL da pasta `database/` na primeira inicialização;
4. monta o dashboard em outro container;
5. conecta o dashboard ao banco e mostra os dados no navegador.

Na prática, o fluxo fica assim:

1. o PostgreSQL inicia;
2. o banco cria as tabelas `clients`, `users`, `categories` e `tickets`;
3. os dados ficticios sao inseridos;
4. o dashboard consulta essas tabelas;
5. você acessa a interface pelo navegador.

## Estrutura do banco

O banco possui 4 tabelas principais:

- `clients`: empresas clientes;
- `users`: equipe interna de TI;
- `categories`: tipos de chamados;
- `tickets`: chamados de suporte.

### Relacionamento entre as tabelas

- cada chamado (`tickets`) pertence a um cliente;
- cada chamado possui um responsável da equipe;
- cada chamado pertence a uma categoria.

Em termos simples:

- `clients` diz quem abriu o problema;
- `users` diz quem vai atender;
- `categories` diz que tipo de problema e;
- `tickets` guarda o registro do chamado.

## O que aparece no dashboard

Ao abrir o dashboard, você vera:

- total de chamados;
- quantidade de chamados abertos ou em andamento;
- quantidade de chamados resolvidos;
- gráfico por status;
- gráfico por categoria e prioridade;
- tabela com os chamados mais recentes.

## Requisitos

Você precisa ter instalado:

- Docker;
- Docker Compose.

Observação importante:

- em versões mais novas, o Compose ja vem integrado ao Docker e o comando usado e `docker compose`;
- em instalações mais antigas, o comando pode ser `docker-compose`.

Este README vai usar `docker compose`, que e o formato mais atual.

## Tutorial para Linux

### 1. Instale o Docker

Se o Docker ainda não estiver instalado, instale primeiro.

Em distribuições baseadas em Ubuntu, normalmente o processo começa assim:

```bash
sudo apt update
sudo apt install docker.io docker-compose-plugin
```

Depois, inicie o Docker:

```bash
sudo systemctl enable --now docker
```

Para verificar se deu certo:

```bash
docker --version
docker compose version
```

Se aparecer a versão dos dois comandos, esta tudo certo.

### 2. Entre na pasta do projeto

Abra o terminal e va ate a pasta do repositório:

```bash
cd /caminho/para/drp03-pi-database
```

### 3. Suba o projeto

Execute:

```bash
docker compose up --build
```

Esse comando:

- monta o dashboard;
- cria o banco;
- executa os scripts SQL;
- deixa tudo rodando.

Na primeira execução, pode demorar um pouco mais.

### 4. Acesse o dashboard

Quando o processo terminar de subir, abra o navegador e entre em:

```text
http://localhost:8501
```

### 5. Parar o projeto

Para encerrar, volte ao terminal onde o projeto esta rodando e pressione:

```text
Ctrl + C
```

Depois, se quiser garantir que os containers foram encerrados:

```bash
docker compose down
```

## Tutorial para Windows

### 1. Instale o Docker Desktop

No Windows, a forma mais simples é instalar o Docker Desktop.

Passos gerais:

1. acesse o site oficial do Docker;
2. baixe o Docker Desktop;
3. instale normalmente;
4. reinicie o computador se o instalador pedir;
5. abra o Docker Desktop e espere ele ficar ativo.

Para testar, abra o PowerShell ou Prompt de Comando e execute:

```powershell
docker --version
docker compose version
```

### 2. Abra a pasta do projeto

Você pode fazer isso de duas formas:

1. pelo Explorador de Arquivos, abrindo a pasta do projeto;
2. pelo terminal, entrando na pasta com `cd`.

Exemplo no PowerShell:

```powershell
cd C:\caminho\para\drp03-pi-database
```

### 3. Suba o projeto

Execute:

```powershell
docker compose up --build
```

Espere alguns segundos ou minutos, principalmente na primeira vez.

### 4. Acesse o dashboard

Abra o navegador e acesse:

```text
http://localhost:8501
```

### 5. Parar o projeto

No terminal onde o projeto estiver rodando, pressione:

```text
Ctrl + C
```

Se quiser remover os containers em seguida:

```powershell
docker compose down
```

## Como recriar o banco do zero

Isso e importante para quem esta testando.

Os arquivos SQL da pasta `database/` sao executados apenas na primeira criação do banco. Isso acontece porque os dados ficam salvos em um volume Docker.

Se você alterar os scripts SQL e quiser recriar tudo do zero, use:

```bash
docker compose down -v
docker compose up --build
```

O comando `down -v` apaga tambem o volume onde os dados do PostgreSQL ficaram guardados.

## Dados de acesso e portas

### Banco PostgreSQL

- host: `localhost`
- porta: `5432`
- usuario: `admin`
- senha: `adminpassword`
- banco: `consultoria_db`

### Dashboard

- endereco: `http://localhost:8501`

## Possiveis problemas comuns

### A porta 5432 ou 8501 ja esta em uso

Isso significa que outro programa ja esta usando essa porta.

Possiveis solucoes:

- fechar o programa que esta usando a porta;
- alterar a porta no arquivo `docker-compose.yml`.

### O dashboard abriu, mas nao mostrou dados

Espere alguns segundos e atualize a pagina. O banco pode ainda estar finalizando a inicialização.

### Alterei os arquivos SQL e nada mudou

Isso normalmente acontece porque o volume antigo do PostgreSQL ainda existe.

Use:

```bash
docker compose down -v
docker compose up --build
```

## Resumo rapido

Se você quer apenas testar rapidamente, o essencial e:

```bash
docker compose up --build
```

Depois abra:

```text
http://localhost:8501
```

Se quiser apagar tudo e recriar do zero:

```bash
docker compose down -v
docker compose up --build
```

## Objetivo academico do projeto

Este repositório serve como exemplo simples de:

- modelagem basica de banco relacional;
- carga inicial de dados ficticios;
- integracao entre banco de dados e interface visual;
- uso de containers para facilitar testes e apresentações.
