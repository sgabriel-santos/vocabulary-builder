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
    pnpm --dir frontend install

# Sobe o Postgres local e espera ficar saudável
db-up:
    docker compose up -d --wait db

# Para os containers do ambiente local (mantém o volume)
db-down:
    docker compose down

# Postgres + API + frontend em paralelo (Ctrl+C encerra tudo)
dev: db-up
    trap 'kill 0' EXIT; just dev-backend & just dev-frontend & wait

# API com reload (porta API_PORT, padrão 8000)
dev-backend:
    cd backend && uv run uvicorn app.main:create_app --factory --reload --port ${API_PORT:-8000}

# Frontend com HMR em :5173 (proxy de /api para a API_PORT)
dev-frontend:
    pnpm --dir frontend dev

# Build de produção do frontend (gera frontend/dist)
build-frontend:
    pnpm --dir frontend build

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

# Lint do backend (ruff check + format --check)
lint-backend:
    cd backend && uv run ruff check && uv run ruff format --check

# Lint do frontend (eslint + prettier --check)
lint-frontend:
    pnpm --dir frontend lint && pnpm --dir frontend format:check

# Type check do backend (mypy strict)
typecheck-backend:
    cd backend && uv run mypy

# Type check do frontend (tsc)
typecheck-frontend:
    pnpm --dir frontend typecheck

# Todos os testes do backend com cobertura (Docker precisa estar rodando)
test-backend:
    cd backend && uv run pytest --cov --cov-report=xml --cov-report=term

# Testes unitários (sem Docker)
test-unit:
    cd backend && uv run pytest -m unit

# Testes de integração (Postgres via testcontainers)
test-integration:
    cd backend && uv run pytest -m integration

# Testes de API (Postgres via testcontainers + fakes)
test-api:
    cd backend && uv run pytest -m api

# Regenera o client da API (frontend/src/api/schema.d.ts) a partir do OpenAPI do backend
gen-client:
    tmp="$(mktemp --suffix .json)"; \
    trap 'rm -f "$tmp"' EXIT; \
    (cd backend && uv run python -m app.scripts.export_openapi) > "$tmp"; \
    pnpm --dir frontend exec openapi-typescript "$tmp" -o src/api/schema.d.ts
