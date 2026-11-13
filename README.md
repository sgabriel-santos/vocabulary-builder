# Vocabulary Builder

PWA de uso pessoal que transforma palavras e expressões em inglês anotadas no dia a dia em vocabulário ativo: captura, enriquecimento por IA, repetição espaçada (FSRS), pronúncia, diário e estúdio de vídeo.

Backend em FastAPI (Python 3.14) + PostgreSQL 18; frontend em React + Vite (Node 26). Visão, escopo e decisões ficam em [`docs/`](docs/) — comece pelo [`project-overview.md`](docs/project-overview.md) e pelos [ADRs](docs/adr/README.md).

## Pré-requisitos

| Ferramenta | Versão | Instalação |
|---|---|---|
| Docker + Compose | recente | [docs.docker.com](https://docs.docker.com/engine/install/) |
| uv | ≥ 0.12 | [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) (instala o Python 3.14 sozinho) |
| Node | 26 LTS | `nvm install 26` (o projeto fixa a versão em `frontend/.nvmrc`; rode `nvm use` na pasta) |
| pnpm | standalone | `curl -fsSL https://get.pnpm.io/install.sh \| sh -` |
| just | ≥ 1.40 | `uv tool install rust-just` |

## Como rodar

```bash
just setup        # cria o .env a partir do .env.example e instala as dependências do backend
just db-up        # sobe o Postgres local (127.0.0.1:5432) e espera ficar saudável
just migrate      # aplica as migrações
just dev-backend  # API em http://localhost:8000 (docs em /api/docs)
```

Verificação rápida: `curl localhost:8000/api/v1/health` → `{"status":"ok","database":"ok"}`.

> **Portas ocupadas?** Se outro projeto já usa a 5432 ou a 8000, ajuste `POSTGRES_PORT` e/ou `API_PORT` no seu `.env` (ex.: 5433 e 8001). O `compose.yaml`, a API e o `just dev-backend` leem essas variáveis.

## Comandos úteis

| Comando | O que faz |
|---|---|
| `just --list` | Lista todas as receitas |
| `just db-up` / `just db-down` | Sobe / para o Postgres local (o volume é mantido) |
| `just migrate` | `alembic upgrade head` |
| `just migration "mensagem"` | Gera uma migração por autogenerate (revise à mão antes de commitar) |
| `just dev-backend` | API com reload na porta 8000 |

## Variáveis de ambiente

Todas estão documentadas em [`.env.example`](.env.example), agrupadas em aplicação, banco, sessão/autenticação, seed de desenvolvimento e produção. O `just` carrega o `.env` automaticamente; sem ele, a API usa defaults equivalentes aos de desenvolvimento. Em produção, segredos ficam em `/run/secrets` (ver [ADR 0010](docs/adr/0010-docker-images-and-compose-layout.md)).
