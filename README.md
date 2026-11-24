# PingPoli

Sistema web de comunicação e gestão da equipe de Tênis de Mesa da Escola Politécnica da USP. Reúne em um só lugar o quadro de avisos, o calendário de treinos com controle de presença, os campeonatos e inscrições, o registro de partidas set a set com confirmação pelo adversário e um dashboard de desempenho individual e da equipe.

Projeto final da disciplina **PMR3304 – Sistemas de Informação** (Poli-USP, 2026) · Grupo H.

| Integrante | NUSP 
|---|---|---|
| Felipe Rossi Mizutani | 15451697 |
| Vitor Chastinet de Carvalho Daltro | 15492129 |
| Felipe Galvão Gamboa | 15636567 |
| Renan Eizo Oda | 15486682 |

## Como executar

Pré-requisitos: **Python 3.12 ou superior**, **Node.js 20.19 ou superior** e **Git**.

### 1. Baixar o projeto

```bash
git clone https://github.com/FelipeMizutani22/Ping-Poli.git
cd Ping-Poli
```

### 2. Backend (terminal 1)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate              # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo --reset  # cria os dados de demonstração
python manage.py runserver          # API em http://127.0.0.1:8000/api/v1/
```

### 3. Frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

Abra **http://localhost:5173** e entre com um dos usuários abaixo.

### Configuração (opcional)

Os valores padrão já funcionam localmente. Para mudá-los, copie `backend/.env.example` para `backend/.env` e `frontend/.env.example` para `frontend/.env`.

| Variável | Onde | Padrão |
|---|---|---|
| `DJANGO_SECRET_KEY` | backend | chave de desenvolvimento |
| `DJANGO_DEBUG` | backend | `1` |
| `DJANGO_ALLOWED_HOSTS` | backend | `127.0.0.1,localhost` |
| `CORS_ALLOWED_ORIGINS` | backend | `http://localhost:5173,http://127.0.0.1:5173` |
| `VITE_API_URL` | frontend | `http://127.0.0.1:8000/api/v1/` |

## Dados de demonstração

O comando `python manage.py seed_demo --reset` apaga os dados e recria uma equipe completa: 13 usuários, 3 campeonatos, cerca de 90 partidas dos últimos 12 meses, avisos, treinos às terças e quintas com presenças e um treino no dia de hoje, com a janela de presença aberta. Os dados são sempre os mesmos (gerador aleatório com semente fixa). Como o treino de hoje depende do horário, rode o comando pouco antes de demonstrar o sistema.

**Senha de todos os usuários:** `pingpoli123`

| E-mail | Perfil | Situação | Observação |
|---|---|---|---|
| marina.souza@usp.br | Diretora | ativa | Também acessa o `/admin/` do Django |
| rafael.costa@usp.br | Diretor | ativa | Segundo Diretor |
| ana.lima@usp.br | Atleta | ativa | Atleta com mais partidas e histórico de campeonatos |
| bruno.kato@usp.br | Atleta | ativa | Adversário frequente da Ana |
| carla.mendes, diego.alves, elisa.tanaka, felipe.ramos, gabriela.nunes, henrique.sato (@usp.br) | Atleta | ativa | Demais membros da equipe |
| igor.pereira@usp.br | Atleta | inativa | Não consegue entrar |
| julia.martins@usp.br | Atleta | pendente | Aparece em "Solicitações pendentes" |
| lucas.rocha@usp.br | Atleta | recusada | Mostra a mensagem de cadastro recusado |

Os e-mails enviados pelo sistema (aprovação de cadastro, inscrição confirmada etc.) aparecem no terminal do `runserver`; não há servidor de e-mail.

## Testes

```bash
cd backend
python manage.py test
```

São 386 testes automatizados do backend, cobrindo modelos e restrições do banco, regras de negócio, permissões por perfil e os endpoints da API.

## Funcionalidades

**Para todos os atletas**
- Login por e-mail e senha; solicitação de cadastro, que fica pendente até a aprovação da Diretoria.
- Página inicial com resumo, avisos fixados, próximos eventos e sino de notificações.
- Quadro de avisos com fixados no topo, filtro por categoria e marcação de lidos.
- Calendário mensal de treinos e campeonatos; confirmação de presença (própria ou de um colega) dentro da janela do treino; relatório de frequência.
- Campeonatos com categorias e controle de vagas; inscrição e "Minhas inscrições".
- Registro de partidas set a set contra atletas da Poli ou adversários externos, com validação da regra do tênis de mesa (11 pontos com 2 de vantagem). O adversário da Poli confirma ou contesta o placar.
- Dashboard de desempenho com filtros por período, competição e tipo de adversário: indicadores, evolução mensal, resultados por competição, colocações, partidas recentes e adversários mais enfrentados.
- Confronto direto entre dois atletas.
- Meu perfil: edição dos próprios dados e troca de senha.

**Para a Diretoria**
- Gestão de atletas: aprovar ou recusar cadastros, editar dados, inativar e reativar, conceder ou revogar o perfil de Diretor (sempre com ao menos um Diretor ativo).
- Criação, edição, fixação e exclusão de avisos.
- Criação de eventos (inclusive treinos semanais recorrentes), cancelamento e ajuste de presenças com justificativa.
- Frequência da equipe com exportação em CSV.
- Cadastro de campeonatos, gestão de inscritos e registro de colocações.
- Moderação de partidas contestadas, com histórico das alterações.
- Ranking e estatísticas da equipe; consulta do desempenho de qualquer atleta.
- Ações administrativas registradas em auditoria.

## Tecnologias

- **Backend:** Python 3.12+, Django 6.1, Django REST Framework (API REST com autenticação por token), django-cors-headers, SQLite
- **Frontend:** JavaScript, React 19 + Vite, React Router, React-Bootstrap (Bootstrap 5), Recharts

O frontend consome exclusivamente a API REST (`/api/v1/`). O Django não renderiza páginas para o usuário final; a única exceção é o `/admin/`, usado como apoio.

## Estrutura

```
Ping-Poli/
├── backend/
│   ├── config/         Configurações e rotas principais do Django
│   ├── contas/         Atletas, cursos, login, cadastro, perfis e gestão de membros
│   ├── avisos/         Quadro de avisos e leituras
│   ├── calendario/     Eventos, treinos recorrentes, presenças e frequência
│   ├── competicoes/    Campeonatos, categorias, inscrições e resultados
│   ├── partidas/       Partidas, sets, adversários externos, contestação e moderação
│   ├── desempenho/     Cálculos do dashboard, ranking da equipe e confronto direto
│   └── nucleo/         Painel inicial, notificações, auditoria e dados de demonstração
├── frontend/
│   └── src/
│       ├── api/        Funções de acesso à API (um arquivo por app)
│       ├── components/ Componentes compartilhados (barra de navegação, sino, busca de atleta…)
│       ├── contexts/   Sessão do usuário (AuthContext)
│       ├── pages/      Telas, organizadas por módulo
│       └── utils/      Rótulos e formatação
└── docs/
    └── entregas/       Proposta, casos de uso, diagrama ER (pdf + xml) e relatório do modelo de dados
```


## API

Todas as rotas ficam sob `/api/v1/` e, exceto login e cadastro, exigem o cabeçalho `Authorization: Token <token>`.

| Módulo | Principais rotas |
|---|---|
| Autenticação e contas | `auth/login/`, `auth/logout/`, `auth/me/`, `cadastro/`, `cursos/`, `perfil/`, `perfil/senha/`, `atletas/` (gestão pela Diretoria) |
| Avisos | `avisos/`, `avisos/{id}/`, `avisos/{id}/fixar/` |
| Calendário | `calendario/`, `eventos/`, `eventos/{id}/presencas/`, `frequencia/`, `frequencia/equipe/` |
| Competições | `campeonatos/`, `campeonatos/{id}/inscricoes/`, `campeonatos/{id}/resultados/`, `inscricoes/`, `inscricoes/minhas/` |
| Partidas | `partidas/`, `partidas/{id}/confirmar/`, `partidas/{id}/contestar/`, `partidas/{id}/moderar/`, `partidas/{id}/historico/`, `adversarios-externos/` |
| Desempenho | `desempenho/`, `desempenho/equipe/`, `desempenho/confronto/` |
| Núcleo | `painel/`, `notificacoes/` |

## Documentação

A pasta [`docs/entregas`](docs/entregas) reúne os documentos entregues ao longo da disciplina: proposta, especificação de casos de uso, diagrama entidade-relação (PDF e XML do DbDesigner) e relatório do modelo de dados.