# PingPoli

Sistema web de comunicação e gestão da equipe de Tênis de Mesa da Escola Politécnica da USP: quadro de avisos, calendário de treinos e presença, campeonatos e inscrições, registro de partidas set a set com confirmação pelo adversário e um dashboard de desempenho.

Projeto final da disciplina **PMR3304 – Sistemas de Informação** (Poli-USP, 2026) · Grupo H.

| Integrante | NUSP |
|---|---|
| Felipe Galvão Gamboa | 15636567 |
| Felipe Rossi Mizutani | 15451697 |
| Renan Eizo Oda | 15486682 |
| Vitor Chastinet de Carvalho Daltro | 15492129 |

## Tecnologias

- **Backend:** Python 3.12+, Django 6.1, Django REST Framework (API REST com autenticação por token), SQLite
- **Frontend:** React 19 + Vite, React Router, Bootstrap 5, Recharts

## Estrutura

```
Ping-Poli/
├── backend/          API Django (apps: contas, avisos, calendario, competicoes, partidas, desempenho, nucleo)
├── frontend/         Aplicação React
└── docs/
    └── entregas/     Proposta, especificação de casos de uso, diagrama ER (pdf + xml) e relatório do modelo de dados
```

## Como executar

> Instruções provisórias; a versão final acompanha a entrega.

Pré-requisitos: Python 3.12 ou superior, Node.js 20.19 ou superior e Git.

```bash
# Backend (terminal 1)
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver         # API em http://127.0.0.1:8000/api/v1/

# Frontend (terminal 2)
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

Testes do backend: `cd backend && python manage.py test`
