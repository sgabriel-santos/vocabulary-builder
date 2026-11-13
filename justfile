# Ponto de entrada único de comandos do projeto. `just --list` mostra todas as receitas.

set dotenv-load
set shell := ["bash", "-euo", "pipefail", "-c"]

# Lista as receitas
default:
    @just --list

# Instala dependências e cria o .env a partir do .env.example
setup:
    [ -f .env ] || cp .env.example .env
    cd backend && uv sync

# Sobe o Postgres local e espera ficar saudável
db-up:
    docker compose up -d --wait db

# Para os containers do ambiente local (mantém o volume)
db-down:
    docker compose down

# API com reload (porta API_PORT, padrão 8000)
dev-backend:
    cd backend && uv run uvicorn app.main:create_app --factory --reload --port ${API_PORT:-8000}

# Aplica as migrações no banco local
migrate:
    cd backend && uv run alembic upgrade head

# Gera uma migração por autogenerate (revise à mão antes de commitar)
migration msg:
    cd backend && uv run alembic revision --autogenerate -m "{{msg}}"

# Cria um usuário (senha via prompt)
create-user email:
    cd backend && uv run python -m app.cli create-user {{email}}

# Cria o usuário de desenvolvimento (SEED_USER_EMAIL / SEED_USER_PASSWORD)
seed:
    cd backend && uv run python -m app.cli seed-dev
