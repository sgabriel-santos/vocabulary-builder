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
