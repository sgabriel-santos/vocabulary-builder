# Vocabulary Builder

PWA de uso pessoal que transforma palavras e expressões em inglês anotadas no dia a dia em vocabulário ativo: captura, enriquecimento por IA, repetição espaçada (FSRS), pronúncia, diário e estúdio de vídeo.

Backend em FastAPI (Python 3.14) + PostgreSQL 18; frontend em React + Vite (Node 26). Visão, escopo e decisões ficam em [`docs/`](docs/) — comece pelo [`project-overview.md`](docs/project-overview.md) e pelos [ADRs](docs/adr/README.md).

## Pré-requisitos

| Ferramenta | Versão | Instalação |
|---|---|---|
| Docker + Compose | recente | [docs.docker.com](https://docs.docker.com/engine/install/) |
| uv | ≥ 0.12 | [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) (instala o Python 3.14 sozinho) |
| pnpm | standalone (≥ 12) | `curl -fsSL https://get.pnpm.io/install.sh \| sh -` (o Node 26 que o frontend usa é baixado pelo próprio pnpm; ver abaixo) |
| just | ≥ 1.40 | `uv tool install rust-just` |

> **Node 26:** o `frontend/package.json` fixa o Node em `devEngines.runtime`; o pnpm baixa essa versão e roda os scripts com ela, mesmo que o Node padrão do sistema seja outro. Para usar o Node 26 direto no shell, há o `frontend/.nvmrc` (`nvm use`). No Ubuntu/WSL, o binário do Node 26 precisa da `libatomic1` (`sudo apt-get install -y libatomic1`).

## Como rodar

```bash
just setup        # cria o .env a partir do .env.example, instala as dependências (backend e frontend) e os hooks de pre-commit
just db-up        # sobe o Postgres local (127.0.0.1:5432) e espera ficar saudável
just migrate      # aplica as migrações
just seed         # cria o usuário de desenvolvimento (dev@example.com / dev-password-123)
just dev          # Postgres + API (:8000) + frontend (:5173); Ctrl+C encerra tudo
```

Abra **http://localhost:5173** e entre com `dev@example.com` / `dev-password-123`. O Vite faz proxy de `/api` para a API, reproduzindo a mesma origem da produção.

Verificação rápida da API: `curl localhost:8000/api/v1/health` → `{"status":"ok","database":"ok"}`.

Login direto pela API (requests que alteram estado exigem o header `Origin`):

```bash
curl -i -c cookies.txt -H "Origin: http://localhost:8000" -H "Content-Type: application/json" \
  -d '{"email":"dev@example.com","password":"dev-password-123"}' localhost:8000/api/v1/auth/login
curl -b cookies.txt localhost:8000/api/v1/auth/me
```

> **Portas ocupadas?** Se outro projeto já usa a 5432 ou a 8000, ajuste `POSTGRES_PORT` e/ou `API_PORT` no seu `.env` (ex.: 5433 e 8001). O `compose.yaml`, a API, o `just dev-backend` e o proxy do Vite leem essas variáveis.

## Comandos úteis

| Comando | O que faz |
|---|---|
| `just --list` | Lista todas as receitas |
| `just db-up` / `just db-down` | Sobe / para o Postgres local (o volume é mantido) |
| `just migrate` | `alembic upgrade head` |
| `just migration "mensagem"` | Gera uma migração por autogenerate (revise à mão antes de commitar) |
| `just dev` | Postgres + API + frontend em paralelo |
| `just dev-backend` / `just dev-frontend` | Só a API (reload, porta `API_PORT`) / só o frontend (HMR, porta 5173) |
| `just build-frontend` | Build de produção do frontend (`frontend/dist`, com service worker e manifest da PWA) |
| `just gen-client` | Regenera `frontend/src/api/schema.d.ts` a partir do OpenAPI; rode sempre que mudar rotas ou schemas |
| `just seed` | Cria o usuário de desenvolvimento (idempotente; recusado em produção) |
| `just create-user <email>` | Cria um usuário (senha via prompt, mínimo de 8 caracteres) |
| `just lint` / `just typecheck` / `just test` | Backend + frontend (o `test` do backend precisa do Docker) |
| `just format` | Formata backend (ruff) e frontend (prettier) |
| `just lint-backend` / `just typecheck-backend` | Ruff (lint + formato) / mypy strict |
| `just lint-frontend` / `just typecheck-frontend` | ESLint + Prettier / `tsc` |
| `just test-backend` | Todos os testes do backend com cobertura (precisa do Docker) |
| `just test-frontend` | Vitest + Testing Library + MSW |
| `just test-unit` / `test-integration` / `test-api` | Testes por camada (`unit` roda sem Docker) |
| `just build` | Build do frontend e das imagens Docker `vocab-api:local` e `vocab-web:local` |
| `uvx pre-commit run --all-files` | Roda todos os hooks (ruff, ESLint, Prettier, gitleaks, checagens de arquivo) em todo o repositório |

## Qualidade, CI e produção

- **Pre-commit** (instalado pelo `just setup`): hooks rápidos a cada commit; configuração em [`.pre-commit-config.yaml`](.pre-commit-config.yaml).
- **CI** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)): em todo PR e push fora da `main`, roda as mesmas receitas `just lint-*`, `typecheck-*` e `test-*`, verifica se o client gerado está em dia com a API (`contract`) e procura segredos com gitleaks.
- **Produção**: imagens `api` ([`backend/Dockerfile`](backend/Dockerfile)) e `web` ([`frontend/Dockerfile`](frontend/Dockerfile), Caddy + SPA), orquestradas por [`deploy/compose.prod.yaml`](deploy/compose.prod.yaml) num VPS. Setup do servidor, deploy, rollback e operação: [`deploy/README.md`](deploy/README.md).

## Variáveis de ambiente

Todas estão documentadas em [`.env.example`](.env.example), agrupadas em aplicação, banco, sessão/autenticação, seed de desenvolvimento e produção. O `just` carrega o `.env` automaticamente; sem ele, a API usa defaults equivalentes aos de desenvolvimento. Em produção, segredos ficam em `/run/secrets` (ver [ADR 0010](docs/adr/0010-docker-images-and-compose-layout.md)).
