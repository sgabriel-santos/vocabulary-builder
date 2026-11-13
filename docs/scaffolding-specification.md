# Especificação do Scaffolding — Vocabulary Builder (E0)

> **Propósito:** descrever de forma completa o boilerplate inicial do projeto (entrega **E0 — walking skeleton**, ver [`delivery-plan.md`](delivery-plan.md)). Este documento deve bastar para montar o scaffolding do zero sem perguntas adicionais.
>
> **Origem:** decisões tomadas no brainstorm de scaffolding (skill `scaffolding-brainstorm`), registradas como ADRs em [`docs/adr/`](adr/README.md).
>
> **Status:** aprovado · **Data:** 2026-11-12 · **Revisão:** E0 enxugada (backup movido para a E1, rollback manual, sem fakes em memória de repositórios, deploy em workflow único, Dependabot mensal) · **2ª revisão:** auth sem ports de repositório, deploy sem `command=` no SSH, client versiona só o `schema.d.ts`, sem `just prod-local` e sem hook `commit-msg`, tabelas iniciais mínimas
>
> **Fonte da verdade após a implementação:** os trechos de referência deste documento (Dockerfile, Caddyfile, compose, workflows, receitas) servem para montar o scaffolding. Depois que os arquivos reais existirem, **eles prevalecem**; esta spec não é atualizada para espelhá-los, apenas quando uma decisão mudar.
>
> **Fora deste documento:** cronograma, tarefas e ordem de implementação (ficam no Blueprint gerado pela skill `scaffolding-blueprint`).

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Estrutura de diretórios](#2-estrutura-de-diretórios)
3. [Stack e dependências](#3-stack-e-dependências)
4. [Convenções](#4-convenções)
5. [Configuração de ambiente](#5-configuração-de-ambiente)
6. [Autenticação](#6-autenticação)
7. [Backend: organização e padrões](#7-backend-organização-e-padrões)
8. [Frontend: organização e padrões](#8-frontend-organização-e-padrões)
9. [Ferramentas de qualidade](#9-ferramentas-de-qualidade)
10. [Estratégia de testes](#10-estratégia-de-testes)
11. [Docker e deploy](#11-docker-e-deploy)
12. [CI/CD](#12-cicd)
13. [Comandos essenciais](#13-comandos-essenciais)
14. [Critério de pronto da E0](#14-critério-de-pronto-da-e0)

---

## 1. Visão geral

### 1.1 Propósito

O Vocabulary Builder é uma PWA de uso pessoal (single-user, com `user_id` no modelo para não bloquear multiusuário) para transformar palavras anotadas em vocabulário ativo. Visão, escopo e domínio completos: [`project-overview.md`](project-overview.md).

### 1.2 Escopo da E0

A E0 **não entrega nenhuma funcionalidade `F-xx`**. Ela entrega o caminho completo do código até a produção:

- Monorepo `backend/` (FastAPI) + `frontend/` (React + TS + Vite).
- Backend em camadas (hexagonal), `GET /api/v1/health`, configuração via ambiente, logs estruturados, Alembic com migração inicial (`users`, `sessions`).
- Autenticação por e-mail + senha com sessão server-side (login, logout, `me`, rota protegida).
- Frontend com roteamento, layout base, PWA instalável, client gerado do OpenAPI, tela de login e tela protegida que exibe o status do backend.
- Ferramentas de qualidade e um teste de exemplo em cada camada de teste.
- `compose.yaml` local apenas com Postgres.
- CI (lint, tipos, testes, drift do contrato) e CD (deploy automático na `main` com smoke test; rollback manual).
- Produção com HTTPS em VPS e segredos fora do repositório.

**Fora do escopo da E0:** qualquer `F-xx`, fila/worker, Redis, object storage, ports de provedores de IA (entram nas entregas que os usam), Playwright, **backup externo** (entra na E1, antes de existirem dados reais; seção 11.7) e **rollback automático** (seção 12.2).

### 1.3 Decisões centrais

| Tema | Decisão | ADR |
|---|---|---|
| Hospedagem | VPS Hostinger KVM 2 (BR) + Docker Compose + Caddy (HTTPS automático, mesma origem) | [0001](adr/0001-hosting-vps-compose-caddy.md) |
| Banco | Postgres 18 em container no VPS + backup diário criptografado externo (a partir da E1) | [0002](adr/0002-postgres-on-vps-with-offsite-backup.md) |
| Autenticação | E-mail + senha (Argon2) + sessão server-side em cookie `HttpOnly` | [0003](adr/0003-auth-password-server-side-sessions.md) |
| Python | `uv` + Python 3.14 | [0004](adr/0004-python-tooling-uv-python-314.md) |
| Node | pnpm + Node 26 LTS | [0005](adr/0005-frontend-tooling-pnpm-node-26.md) |
| Persistência | SQLAlchemy 2.0 async + psycopg 3; domínio separado onde há regra | [0006](adr/0006-persistence-sqlalchemy-psycopg-domain-separation.md) |
| Testes backend | unit / integration / api + fakes; Postgres via testcontainers | [0007](adr/0007-backend-testing-testcontainers.md) |
| Roteamento | TanStack Router com rotas por arquivo | [0008](adr/0008-frontend-routing-tanstack-router.md) |
| Client da API | openapi-typescript + openapi-fetch + openapi-react-query; versionado com checagem de drift | [0009](adr/0009-api-client-openapi-fetch-versioned.md) |
| Docker | Imagens `api` e `web`; compose de dev e de prod separados; migração one-off | [0010](adr/0010-docker-images-and-compose-layout.md) |
| CI/CD | GitHub Actions; deploy automático na `main` com smoke test; rollback manual | [0011](adr/0011-ci-cd-auto-deploy-with-rollback.md) |
| Branching | Branches curtas + PR + squash merge | [0012](adr/0012-branching-pr-squash-merge.md) |

Padrões de baixo impacto (task runner, hooks, logging, type checker, UI, lint, PWA, nomenclatura etc.) estão nas seções correspondentes deste documento.

### 1.4 Topologia de produção

```
                Internet (HTTPS 443 / HTTP 80 → redirect)
                                │
         DNS: vocab.<domínio>  →  IP do VPS (registro A)
                                │
┌─────────────────────────── VPS (Ubuntu 24.04 + Docker) ─────────────────────────┐
│  ┌──────────────────────────────────────────────┐                               │
│  │ web (Caddy + build do SPA)  :80 :443 :443/udp│  ← único serviço com portas   │
│  │   /api/*  → reverse_proxy api:8000           │                               │
│  │   /*      → arquivos estáticos (fallback SPA)│                               │
│  └───────────────────────┬──────────────────────┘                               │
│              rede interna│do Compose                                            │
│  ┌───────────────────────▼──────┐   ┌────────────────────┐   ┌───────────────┐  │
│  │ api (FastAPI / uvicorn)      │──▶│ db (postgres:18)   │◀──│ migrate       │  │
│  └──────────────────────────────┘   │ volume db_data     │   │ (one-off)     │  │
│                                     └─────────┬──────────┘   └───────────────┘  │
│  systemd timer → deploy/backup.sh (E1) ───────┘ pg_dump → age → rclone          │
└──────────────────────────────────────────────────┼──────────────────────────────┘
                                                   ▼
                                    Storage externo (Backblaze B2 ou Cloudflare R2)
```

---

## 2. Estrutura de diretórios

```
vocabulary-builder/
├── AGENTS.md                        # Instruções canônicas para agentes de IA
├── CLAUDE.md                        # Regras de commit + importa AGENTS.md
├── README.md                        # Apresentação curta + "como rodar" (aponta para esta spec)
├── justfile                         # Task runner: ponto de entrada único de todos os comandos (seção 13)
├── compose.yaml                     # Compose de DESENVOLVIMENTO: apenas Postgres
├── .env.example                     # Todas as variáveis de ambiente documentadas, sem valores reais
├── .editorconfig                    # Indentação, charset, EOL
├── .gitattributes                   # Força LF em todos os arquivos de texto
├── .gitignore
├── .pre-commit-config.yaml          # Hooks rápidos (seção 9.2)
├── .github/
│   ├── dependabot.yml               # Atualizações mensais agrupadas
│   └── workflows/
│       ├── ci.yml                   # Lint, tipos, testes, drift do contrato, gitleaks (reutilizável via workflow_call)
│       └── deploy.yml               # Push na main: chama ci.yml → build/push GHCR → deploy SSH + smoke test
├── deploy/                          # Tudo que vive no VPS (copiado a cada deploy, exceto segredos)
│   ├── README.md                    # Setup inicial do VPS, DNS, backup e restore (runbook)
│   ├── compose.prod.yaml            # Compose de PRODUÇÃO: web, api, migrate, db
│   ├── deploy.sh                    # Executado via SSH: pull, up -d, smoke test
│   ├── backup.sh                    # (E1) pg_dump → age → rclone → ping de monitoramento
│   ├── systemd/                     # (E1)
│   │   ├── vocab-backup.service     # Unidade que executa backup.sh
│   │   └── vocab-backup.timer       # Agenda diária
│   └── secrets/
│       └── .gitkeep                 # Pasta dos arquivos de segredo NO VPS (conteúdo nunca versionado)
├── docs/
│   ├── project-overview.md          # Visão, escopo, domínio, roadmap
│   ├── delivery-plan.md             # Entregas E0–E5
│   ├── scaffolding-specification.md # Este documento
│   └── adr/                         # Architecture Decision Records (NNNN-titulo.md)
│
├── backend/
│   ├── pyproject.toml               # Dependências (PEP 621), config de ruff, mypy, pytest, coverage
│   ├── uv.lock                      # Lockfile (versionado)
│   ├── .python-version              # 3.14
│   ├── Dockerfile                   # Imagem "api" (multi-stage, seção 11.1)
│   ├── .dockerignore
│   ├── alembic.ini
│   ├── migrations/
│   │   ├── env.py                   # Usa o metadata dos modelos e a URL do Settings
│   │   ├── script.py.mako
│   │   └── versions/                # 0001_initial (users, sessions)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # create_app(): FastAPI, middlewares, routers, operationIds
│   │   ├── api/                     # Camada HTTP: routers e schemas de request/response
│   │   │   ├── deps.py              # Dependencies compartilhadas (sessão de DB, current_user, origin check)
│   │   │   └── v1/
│   │   │       ├── router.py        # Agrega os routers da v1 sob /api/v1
│   │   │       ├── health.py        # GET /api/v1/health
│   │   │       ├── auth.py          # POST /auth/login, POST /auth/logout, GET /auth/me
│   │   │       └── schemas/         # Modelos Pydantic de request/response (DTOs da API)
│   │   ├── domain/                  # Entidades (dataclasses) e regras puras; sem I/O, sem SQLAlchemy
│   │   │   └── auth.py              # Ex.: regra de expiração/renovação de sessão
│   │   ├── application/             # Casos de uso: orquestram domínio + ports
│   │   │   └── auth/                # login, logout, resolve_session, create_user (usam a AsyncSession direto)
│   │   ├── ports/                   # Interfaces (typing.Protocol)
│   │   │   ├── clock.py             # Clock: now() -> datetime (UTC)
│   │   │   └── password_hasher.py   # PasswordHasher: hash/verify
│   │   ├── adapters/                # Implementações dos ports
│   │   │   ├── clock.py             # SystemClock
│   │   │   ├── security/
│   │   │   │   └── argon2_hasher.py # Argon2PasswordHasher
│   │   │   └── db/
│   │   │       ├── base.py          # DeclarativeBase, convenções de nome de constraints, mixins (id, timestamps)
│   │   │       ├── engine.py        # create_async_engine / async_sessionmaker
│   │   │       └── models/          # Modelos SQLAlchemy (Mapped[...]): user.py, session.py
│   │   ├── core/                    # Infraestrutura transversal
│   │   │   ├── config.py            # Settings (pydantic-settings)
│   │   │   ├── logging.py           # Configuração do structlog
│   │   │   ├── middleware.py        # Request-id, logging de acesso
│   │   │   ├── rate_limit.py        # Rate limit em memória para o login
│   │   │   └── container.py         # Composition root: providers (clock, hasher, sessão de DB)
│   │   ├── cli/
│   │   │   └── __main__.py          # `create-user <email>` (senha via prompt) e `seed-dev`
│   │   └── scripts/
│   │       └── export_openapi.py    # Exporta app.openapi() para JSON sem subir servidor
│   └── tests/
│       ├── conftest.py              # Fixtures globais (settings de teste, clock fake)
│       ├── fakes/                   # Fakes de ports de provedores/infra: FakeClock, FakePasswordHasher
│       ├── unit/                    # Domínio e casos de uso com fakes (sem DB)
│       ├── integration/             # Migrações e constraints contra Postgres real (testcontainers)
│       │   └── conftest.py          # Container Postgres, alembic upgrade head, sessão com rollback
│       └── api/                     # App completo via httpx + ASGITransport, DB real, provedores fake
│           └── conftest.py          # AsyncClient com dependency_overrides
│
└── frontend/
    ├── package.json                 # Scripts, deps, "packageManager": "pnpm@<versão>", "engines"
    ├── pnpm-lock.yaml               # Lockfile (versionado)
    ├── .nvmrc                       # 26
    ├── Dockerfile                   # Imagem "web" (build do SPA + Caddy, seção 11.2)
    ├── .dockerignore
    ├── Caddyfile                    # Configuração do Caddy embutida na imagem web
    ├── index.html
    ├── vite.config.ts               # React, TanStack Router plugin, Tailwind, PWA, proxy /api (dev)
    ├── vitest.config.ts             # (ou bloco test no vite.config.ts)
    ├── tsconfig.json                # strict: true
    ├── eslint.config.js             # Flat config
    ├── .prettierrc
    ├── components.json              # Config do shadcn/ui
    ├── public/
    │   ├── favicon.svg
    │   └── icons/                   # pwa-192.png, pwa-512.png, maskable-512.png, apple-touch-icon.png
    └── src/
        ├── main.tsx                 # Bootstrap: QueryClient, Router, registro do service worker
        ├── index.css                # Tailwind v4 (@import "tailwindcss") + tokens do tema
        ├── routeTree.gen.ts         # GERADO pelo plugin do TanStack Router (versionado, não editar)
        ├── routes/                  # Rotas por arquivo
        │   ├── __root.tsx           # Layout raiz (shell, Toaster, prompt de atualização da PWA)
        │   ├── login.tsx            # /login (pública)
        │   ├── _authenticated.tsx   # Layout protegido: beforeLoad verifica /auth/me, senão redirect /login
        │   └── _authenticated/
        │       └── index.tsx        # / (home protegida: status do backend)
        ├── api/
        │   ├── schema.d.ts          # GERADO (just gen-client) — versionado, não editar
        │   ├── client.ts            # createClient<paths>() do openapi-fetch + $api (openapi-react-query)
        │   └── query-client.ts      # Instância do QueryClient e defaults
        ├── features/                # Código por funcionalidade (cresce a cada entrega)
        │   ├── auth/                # LoginForm.tsx, useLogin.ts, useLogout.ts (invalidam `me` e redirecionam)
        │   └── health/              # HealthStatus.tsx (usa $api direto, sem hook próprio)
        ├── components/
        │   ├── ui/                  # Componentes shadcn/ui (gerados via CLI, editáveis)
        │   └── layout/              # AppShell.tsx, etc.
        ├── lib/                     # Utilitários (cn(), formatação)
        └── test/
            ├── setup.ts             # Testing Library + MSW server
            └── handlers.ts          # Handlers MSW tipados (openapi-msw)
```

Regras de localização:

- **Regra de negócio** → `backend/app/domain/` (puro) e `backend/app/application/` (orquestração). Nunca em routers.
- **Acesso a banco** → modelos e engine em `backend/app/adapters/db/`. A camada `application/` usa a `AsyncSession` e os modelos ORM diretamente em **CRUD e leituras simples**, devolvendo DTOs/dataclasses. Repositório (port em `ports/` + implementação em `adapters/db/repositories/`) só para **agregados com regra de negócio**, e o primeiro nasce junto com o primeiro agregado desse tipo (ex.: `Card`/FSRS na E3), não antes.
- **Provedores externos** (a partir da E2) → port em `ports/`, implementação em `adapters/<tipo>/`, fake em `tests/fakes/`.
- **Frontend**: telas e hooks de cada funcionalidade em `src/features/<feature>/`; rotas em `src/routes/` são finas (montam componentes de `features/`).

---

## 3. Stack e dependências

Versões: as **linhas** abaixo são decisões; as versões exatas (patch/minor) são fixadas nos lockfiles (`uv.lock`, `pnpm-lock.yaml`) e nas tags das imagens no momento da implementação. Antes de usar qualquer biblioteca, verificar a documentação atual (overview §17.7).

### 3.1 Runtimes e ferramentas

| Item | Versão | Motivo |
|---|---|---|
| Python | **3.14** (`.python-version`) | Estável com wheels de todas as deps críticas (spaCy, Pydantic v2). 3.15 bloqueado: spaCy declara `<3.15`. |
| uv | versão fixada no CI e no Dockerfile | Gerencia Python, venv e lock; muito rápido em CI/Docker. |
| Node.js | **26 LTS** (`.nvmrc`, `engines: ">=26"`) | Active LTS mais recente; usado só para build/test do frontend. |
| pnpm | fixado em `packageManager` | Rápido, estrito (sem dependências fantasmas). Corepack não vem mais com o Node: instalar standalone. |
| just | via `uv tool install rust-just` | Task runner (seção 13). |
| Docker Engine + Compose v2 | atual | Dev (Postgres) e produção. |
| PostgreSQL | **18** (`postgres:18-alpine`, minor fixada) | Mesma versão em dev, testes e produção. |
| Caddy | **2.x** (`caddy:2.<x>-alpine`) | Proxy reverso, HTTPS automático, arquivos estáticos. |

### 3.2 Backend — dependências de runtime

| Pacote | Motivo |
|---|---|
| `fastapi` | Framework HTTP (decisão do overview). |
| `uvicorn[standard]` | Servidor ASGI. |
| `pydantic` (v2) | Schemas e validação. |
| `pydantic-settings` | Configuração tipada a partir de env e `/run/secrets`. |
| `sqlalchemy[asyncio]` (2.0+) | ORM async com modelos tipados (`Mapped`). |
| `psycopg[binary]` (3.x) | Driver Postgres único para async e sync. |
| `alembic` | Migrações. |
| `structlog` | Logs estruturados. |
| `argon2-cffi` | Hash de senha (Argon2id). |

### 3.3 Backend — dependências de desenvolvimento (`[dependency-groups] dev`)

| Pacote | Motivo |
|---|---|
| `pytest`, `pytest-asyncio`, `pytest-cov` | Testes, suporte async, cobertura. |
| `httpx` | `AsyncClient` + `ASGITransport` nos testes de API. |
| `testcontainers[postgres]` | Postgres efêmero nos testes de integração e API. |
| `ruff` | Lint + format. |
| `mypy` | Type checking `strict` (com plugin `pydantic.mypy`). |
| `pre-commit` | Executado via `uvx`; listado para referência. |

### 3.4 Frontend — dependências de runtime

| Pacote | Motivo |
|---|---|
| `react`, `react-dom` | UI (decisão do overview). |
| `@tanstack/react-router` | Roteamento tipado (ADR 0008). |
| `@tanstack/react-query` | Estado de servidor. |
| `openapi-fetch` | Client HTTP tipado pelo schema OpenAPI. |
| `openapi-react-query` | Hooks `useQuery`/`useMutation` tipados sobre o openapi-fetch. |
| `tailwindcss` (v4) + `@tailwindcss/vite` | Estilos. |
| Dependências do shadcn/ui (`class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`, `@radix-ui/*` conforme componentes) | Componentes de UI copiados para `src/components/ui/`. |

### 3.5 Frontend — dependências de desenvolvimento

| Pacote | Motivo |
|---|---|
| `vite`, `@vitejs/plugin-react` | Build/dev server. |
| `typescript` | `strict: true`. |
| `@tanstack/router-plugin` | Gera `routeTree.gen.ts` a partir de `src/routes/`. |
| `vite-plugin-pwa` | Manifest + service worker. |
| `openapi-typescript` | Gera `schema.d.ts` a partir do OpenAPI exportado pelo backend. |
| `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom` | Testes de componentes. |
| `msw`, `openapi-msw` | Mock da API tipado. |
| `eslint`, `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `eslint-config-prettier` | Lint. |
| `prettier`, `prettier-plugin-tailwindcss` | Formatação. |

### 3.6 Infraestrutura e serviços externos

| Item | Escolha | Observação |
|---|---|---|
| VPS | Hostinger KVM 2 (2 vCPU / 8 GB / 100 GB NVMe), data center Brasil, x86_64 | Ubuntu 24.04 LTS sem painel. |
| Domínio / DNS | Registro.br, DNS do Registro.br | Registro `A` `vocab` → IP do VPS (e `AAAA` se houver IPv6). |
| Registry | GHCR (`ghcr.io/sgabriel-santos/vocab-api`, `.../vocab-web`) | Tags = SHA do commit. |
| Backup externo (E1) | Backblaze B2 ou Cloudflare R2 | Camada gratuita basta. |
| Monitoramento (opcional) | UptimeRobot (uptime de `/api/v1/health`) e Healthchecks.io (ping do backup) | Gratuitos. |

---

## 4. Convenções

### 4.1 Idioma

- Código, nomes de arquivos, tabelas, endpoints, commits, branches: **inglês**.
- Documentação e comentários: português (pt-BR) permitido.
- Textos da interface: **pt-BR**, escritos diretamente nos componentes (sem biblioteca de i18n).

### 4.2 Nomenclatura

| Contexto | Convenção | Exemplo |
|---|---|---|
| Módulos/pacotes Python | `snake_case` | `password_hasher.py` |
| Classes Python | `PascalCase` | `Argon2PasswordHasher` |
| Funções/variáveis Python | `snake_case` | `resolve_session()` |
| Ports | substantivo do papel, sem prefixo `I` | `Clock`, `PasswordHasher` |
| Adapters | tecnologia + papel | `SystemClock`, `Argon2PasswordHasher` |
| Fakes | `Fake` / `InMemory` + papel | `FakeClock`, `FakePasswordHasher` |
| Tabelas | plural `snake_case` | `users`, `sessions` |
| Colunas | `snake_case`; FKs `<entidade>_id`; timestamps `*_at` (UTC, `timestamptz`) | `user_id`, `expires_at` |
| IDs | UUID (v4 ou v7) gerado na aplicação | — |
| Constraints | convenção de nomes no `MetaData` (`pk_`, `fk_`, `uq_`, `ix_`, `ck_`) | `uq_users_email` |
| Endpoints | prefixo `/api/v1`, recursos no plural, kebab-case | `/api/v1/auth/login` |
| JSON da API | `snake_case` (sem alias de camelCase) | `expires_at` |
| operationId | `<tag>-<nome da função>` via `generate_unique_id_function` | `auth-login` |
| Componentes React | `PascalCase.tsx` | `LoginForm.tsx` |
| Hooks | `useX.ts` | `useCurrentUser.ts` |
| Demais arquivos TS | `kebab-case.ts` | `query-client.ts` |
| Rotas (TanStack) | convenção de arquivos do TanStack Router | `_authenticated/index.tsx` |
| Testes Python | `test_*.py`, funções `test_<comportamento>` | `test_login_rejects_wrong_password` |
| Testes TS | `*.test.ts(x)` ao lado do arquivo testado | `LoginForm.test.tsx` |

### 4.3 Git: branches, PRs e commits

- **Branches curtas** a partir da `main`: `feat/F-01-term-capture`, `fix/...`, `chore/...`, `docs/...`, `refactor/...`, `test/...`, `ci/...`.
- **Toda mudança chega à `main` por PR.** Ruleset da `main`: sem push direto, status checks do CI obrigatórios, histórico linear, sem force push. Sem aprovação obrigatória (projeto solo).
- **Squash merge**: o título do PR vira o commit na `main` e deve seguir Conventional Commits, referenciando `F-xx` quando aplicável (ex.: `feat(capture): add term capture and bulk import (F-01)`).
- **Commits**: regras do [`CLAUDE.md`](../CLAUDE.md) (inglês, Conventional Commits, título imperativo ≤ ~72 caracteres, corpo opcional em tópicos, **sem atribuição de IA**, aprovação explícita do usuário antes de cada commit feito por agente). Com squash merge, o que chega à `main` é o **título do PR**, conferido no momento do merge; por isso não há hook `commit-msg`.

### 4.4 Banco e migrações

- Toda mudança de schema via Alembic (`just migration "mensagem"`), revisada manualmente após o autogenerate.
- **Diretriz (não regra): preferir migrações compatíveis com a versão anterior da aplicação.** O rollback (manual, seção 12.2) volta o código, não o schema. Para mudanças destrutivas (remover/renomear coluna), avaliar caso a caso: em um app single-user, alguns minutos fora do ar são aceitáveis; se o rollback for necessário depois de uma migração destrutiva, faça `alembic downgrade` antes de reimplantar a tag anterior.
- Timestamps em UTC (`timestamptz`).

### 4.5 ADRs

- `docs/adr/NNNN-titulo-em-kebab-case.md`, numeração sequencial, formato: Status, Data, Contexto, Decisão, Consequências.
- Uma decisão que substitui outra marca a anterior como `Substituída por NNNN`.

---

## 5. Configuração de ambiente

### 5.1 Princípios

- Toda configuração do backend passa por `app/core/config.py` (`Settings`, `pydantic-settings`), validada no boot.
- Ordem de precedência: variáveis de ambiente > arquivo `.env` (dev) > valores padrão. Segredos em produção vêm de arquivos em `/run/secrets/` (`secrets_dir`), não de variáveis de ambiente.
- `.env.example` (raiz) é a referência versionada; `.env` nunca é versionado.
- O frontend **não tem variáveis sensíveis**. Como API e SPA estão na mesma origem, o client usa caminhos relativos (`/api/v1/...`) e não precisa de `VITE_API_URL`.

### 5.2 `.env.example`

```dotenv
# ---------- Aplicação ----------
APP_ENV=development              # development | test | production
APP_DOMAIN=localhost             # Produção: vocab.<domínio> (usado pelo Caddy e pela checagem de Origin)
LOG_LEVEL=INFO                   # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT=console               # console (dev) | json (produção)

# ---------- Banco ----------
POSTGRES_HOST=localhost          # Produção: db
POSTGRES_PORT=5432
POSTGRES_DB=vocab
POSTGRES_USER=vocab
POSTGRES_PASSWORD=vocab          # Somente dev. Produção: arquivo deploy/secrets/postgres_password

# ---------- Sessão / autenticação ----------
SESSION_COOKIE_NAME=vocab_session
SESSION_TTL_DAYS=60              # Expiração deslizante
SESSION_COOKIE_SECURE=false      # true em produção (HTTPS)
LOGIN_RATE_LIMIT=5/minute        # Tentativas por IP

# ---------- Seed de desenvolvimento (just seed; recusado em produção) ----------
SEED_USER_EMAIL=dev@example.com
SEED_USER_PASSWORD=dev-password-123

# ---------- Produção (lidas pelo compose.prod.yaml) ----------
IMAGE_TAG=                       # SHA do commit em produção (definido pelo deploy.sh)
```

### 5.3 O que cada variável controla

| Variável | Uso |
|---|---|
| `APP_ENV` | Ajusta defaults (formato de log, cookies `Secure`, docs do OpenAPI: `/api/docs` habilitado fora de produção). |
| `APP_DOMAIN` | Origem esperada (`https://<APP_DOMAIN>`) na checagem de `Origin`; site do Caddyfile em produção. |
| `LOG_LEVEL`, `LOG_FORMAT` | Configuração do structlog. |
| `POSTGRES_*` | Montam a URL `postgresql+psycopg://...` no `Settings` (propriedade `database_url`). |
| `SESSION_*` | Nome, validade e flag `Secure` do cookie de sessão. |
| `LOGIN_RATE_LIMIT` | Limite de tentativas de login por IP. |
| `SEED_USER_*` | Credenciais do usuário criado por `just seed` (só fora de produção). |
| `IMAGE_TAG` | Tag das imagens no `compose.prod.yaml`. |

### 5.4 Segredos em produção

Arquivos no VPS em `/opt/vocab/deploy/secrets/` (diretório dono `deploy`, `chmod 700`; arquivos `chmod 444`), montados via `secrets:` do Compose. Sem Swarm, o secret é um bind mount que preserva dono e modo do host; o processo da `api` roda como uid 1000, então o arquivo precisa ser legível por ele, e a proteção fica no diretório (detalhes em `deploy/README.md`):

| Arquivo | Consumidor | Montado como |
|---|---|---|
| `postgres_password` | `db` (`POSTGRES_PASSWORD_FILE`) e `api`/`migrate` | `/run/secrets/postgres_password` |

O `Settings` lê `postgres_password` de `/run/secrets` (campo `postgres_password`). Novos segredos (chaves de IA a partir da E2) seguem o mesmo padrão. O `.env` de produção (`/opt/vocab/.env`, `chmod 600`) contém apenas configuração não sensível.

---

## 6. Autenticação

### 6.1 Modelo

- **Sem cadastro público.** Usuários são criados por CLI: `just create-user <email>` (senha pedida via prompt, nunca como argumento). Em produção: `docker compose -f compose.prod.yaml run --rm api python -m app.cli create-user <email>`.
- **Senha**: Argon2id (`argon2-cffi`), parâmetros padrão da biblioteca; rehash automático se os parâmetros mudarem.

### 6.2 Tabelas (migração inicial)

**`users`**: `id` (UUID, PK), `email` (único, normalizado em minúsculas), `password_hash`, `created_at`, `updated_at`.

**`sessions`**: `id` (UUID, PK), `user_id` (FK → `users`, `ON DELETE CASCADE`), `token_hash` (único; SHA-256 do token), `created_at`, `last_seen_at`, `expires_at` (indexado).

Apenas as colunas que a E0 usa. Os demais campos do `User` (overview §9.2: `display_name`, `settings`) entram por migração na entrega que os usar.

### 6.3 Fluxos

| Endpoint | Comportamento |
|---|---|
| `POST /api/v1/auth/login` `{email, password}` | Rate limit por IP. Verifica a senha (tempo constante; resposta genérica em erro). Gera token `secrets.token_urlsafe(32)`, grava `sha256(token)` em `sessions` com `expires_at = now + SESSION_TTL_DAYS`, responde `204` com `Set-Cookie`. |
| `POST /api/v1/auth/logout` | Apaga a sessão atual e expira o cookie. `204`. |
| `GET /api/v1/auth/me` | Retorna o usuário autenticado (`id`, `email`) ou `401`. |
| `GET /api/v1/health` | Público. Retorna status da API e do banco (`SELECT 1`). |

**Cookie**: `vocab_session=<token>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=<TTL>` (`Secure` desligado apenas em dev via `SESSION_COOKIE_SECURE=false`).

**Resolução da sessão** (dependency `current_user` em `api/deps.py`): lê o cookie → `sha256` → busca em `sessions` → se `expires_at <= clock.now()`, apaga e retorna `401` → senão atualiza `last_seen_at` e `expires_at` (sliding; para evitar escrita a cada request, renovar apenas se o último `last_seen_at` tiver mais de 1 hora) → injeta o usuário.

**CSRF**: `SameSite=Lax` + mesma origem + dependency que, em `POST/PUT/PATCH/DELETE`, exige header `Origin` igual a `https://<APP_DOMAIN>` (em dev: `http://localhost:5173` e `http://localhost:8000`). Requisições sem `Origin` em métodos mutáveis são rejeitadas (`403`).

**Rate limit**: implementação em memória por IP no endpoint de login (`core/rate_limit.py`), suficiente para uma instância única. O IP real vem dos headers do Caddy (`--proxy-headers` + `--forwarded-allow-ips` restrito à rede interna).

**Relógio**: toda lógica de expiração usa o port `Clock`; testes usam `FakeClock`.

**Frontend**: nunca armazena token (o cookie é `HttpOnly`). O layout `_authenticated` chama `/auth/me` no `beforeLoad` (via `queryClient.ensureQueryData`) e redireciona para `/login` em `401`. Um `401` em qualquer chamada invalida a query `me` e redireciona.

**Futuro (fora da E0)**: TOTP, tela de sessões ativas.

---

## 7. Backend: organização e padrões

### 7.1 Camadas

| Camada | Pode depender de | Não pode depender de |
|---|---|---|
| `domain/` | biblioteca padrão | FastAPI, SQLAlchemy, Pydantic de API, adapters |
| `application/` | `domain/`, `ports/`, modelos ORM e `AsyncSession` (CRUD e leituras simples) | `api/`, adapters concretos de provedores |
| `ports/` | `domain/` | adapters |
| `adapters/` | `ports/`, `domain/`, bibliotecas externas | `api/` |
| `api/` | `application/`, `core/`, schemas | adapters concretos (recebe via DI) |
| `core/` | tudo (é a composition root) | — |

- Entidades de domínio: `@dataclass` (preferencialmente `frozen` ou com métodos de regra explícitos).
- Modelos SQLAlchemy em `adapters/db/models/`; podem ser usados pela `application/`, mas **nunca** chegam à camada `api/` (a `application/` devolve DTOs/dataclasses).
- Schemas de request/response (Pydantic) em `api/v1/schemas/`; nunca retornar modelos ORM diretamente.

### 7.2 Injeção de dependência

- `Depends` do FastAPI. `core/container.py` expõe funções provider (`get_clock`, `get_password_hasher`, `get_db_session`...) que montam os adapters a partir do `Settings`.
- Testes substituem providers com `app.dependency_overrides[...]`.
- Sem biblioteca de container.

### 7.3 Banco

- `create_async_engine` com `postgresql+psycopg://`; `async_sessionmaker(expire_on_commit=False)`.
- Uma sessão por request (dependency com `yield`), commit explícito nos casos de uso.
- Alembic (`migrations/env.py`) usa a mesma URL do `Settings`; pode rodar de forma síncrona com psycopg 3.
- `MetaData(naming_convention=...)` para nomes estáveis de constraints.

### 7.4 Logging e observabilidade

- `structlog` configurado em `core/logging.py`: `LOG_FORMAT=json` em produção, `console` em dev.
- Middleware gera/propaga `X-Request-ID` e o inclui em todos os logs do request; log de acesso com método, rota, status, duração.
- Nunca logar senha, token, cookie ou corpo de requisições de auth.

### 7.5 API

- Prefixo `/api/v1`; documentação interativa em `/api/docs` (desabilitada em produção) e schema em `/api/openapi.json`.
- `generate_unique_id_function` para operationIds estáveis (`<tag>-<função>`), que dão nomes limpos ao client.
- Erros no formato padrão do FastAPI (`{"detail": ...}`).

### 7.6 Ports da E0

| Port | Adapter real | Fake |
|---|---|---|
| `Clock` | `SystemClock` (UTC) | `FakeClock` (tempo controlável) |
| `PasswordHasher` | `Argon2PasswordHasher` | `FakePasswordHasher` (rápido, determinístico) |

**Sem ports de repositório na E0.** `users` e `sessions` são CRUD sem regra de negócio: os casos de uso de `application/auth/` usam a `AsyncSession` diretamente. A única regra (expiração/renovação da sessão) é uma função pura em `domain/auth.py`, testada em `unit/` com `FakeClock`; o fluxo completo é coberto pelos testes de `api/`. O primeiro repositório nasce com o primeiro agregado com regra de negócio (ex.: `Card` na E3).

**Repositórios não ganham fake em memória por padrão.** Os testes de integração e de API usam Postgres real (testcontainers); um `InMemory*Repository` só duplicaria o SQL. Crie um fake de repositório apenas se surgir um teste unitário que realmente precise dele.

Os ports de provedores externos do overview §8.2 (`LLMProvider`, `TTSProvider` etc.) entram nas entregas que os usam.

---

## 8. Frontend: organização e padrões

### 8.1 Roteamento (TanStack Router)

- Rotas por arquivo em `src/routes/`, árvore gerada em `src/routeTree.gen.ts` pelo `@tanstack/router-plugin` (Vite). O arquivo gerado é versionado e nunca editado à mão.
- Rotas protegidas ficam sob o layout `_authenticated` (`beforeLoad` + redirect para `/login?redirect=<path>`).
- Search params com schema de validação por rota (usar o validador nativo do router ou Zod, se adicionado quando necessário).
- Loaders usam `queryClient.ensureQueryData(...)` para pré-carregar dados.

### 8.2 Client da API

- `src/api/client.ts`: `createClient<paths>({ baseUrl: "/" })` (openapi-fetch) e `$api = createQueryClient(client)` (openapi-react-query).
- Componentes chamam `$api.useQuery(...)` / `$api.useMutation(...)` **diretamente** (ex.: `HealthStatus` usa `$api.useQuery("get", "/api/v1/health")`). Extraia um hook em `src/features/<feature>/use*.ts` só quando houver lógica além da chamada ou reuso (ex.: `useLogin`/`useLogout`, que invalidam a query `me` e redirecionam).
- Nunca editar `schema.d.ts` à mão: rodar `just gen-client` após qualquer mudança de rota/schema no backend.

### 8.3 UI

- Tailwind CSS v4 (plugin `@tailwindcss/vite`, configuração CSS-first em `src/index.css`).
- shadcn/ui: componentes adicionados via CLI (`pnpm dlx shadcn@latest add <componente>`) em `src/components/ui/`.
- Mobile-first (prioridade de UX: celular).

### 8.4 PWA (`vite-plugin-pwa`)

- `registerType: "prompt"`: componente no `__root.tsx` mostra "Nova versão disponível — atualizar".
- Manifest: `name` "Vocabulary Builder", `short_name` "Vocab", `lang` "pt-BR", `display` "standalone", `start_url` "/", `theme_color`/`background_color` do tema, ícones 192, 512 e 512 maskable; `apple-touch-icon` no `index.html`.
- Workbox `generateSW`: precache apenas do app shell (JS/CSS/HTML/ícones); **nenhum cache de `/api/*`** (`navigateFallbackDenylist: [/^\/api\//]`). Offline está fora do escopo (overview q12).

### 8.5 Dev server

- `pnpm dev` na porta 5173 com `server.proxy` de `/api` → `http://localhost:8000`, reproduzindo a mesma origem da produção (cookies funcionam sem CORS).

---

## 9. Ferramentas de qualidade

### 9.1 Ferramentas e configuração

| Ferramenta | Escopo | Configuração | Comando |
|---|---|---|---|
| Ruff (lint) | backend | `pyproject.toml`: `target-version = "py314"`, `line-length = 100`, regras `E, F, I, B, UP, SIM, ASYNC, S, RUF` (ajustar `S` em `tests/`) | `just lint` |
| Ruff (format) | backend | padrão do ruff | `just format` |
| mypy | `backend/app` | `strict = true`, `plugins = ["pydantic.mypy"]` | `just typecheck` |
| ESLint | frontend | flat config: `typescript-eslint` (type-checked), `react-hooks`, `react-refresh`, `eslint-config-prettier`; ignora `routeTree.gen.ts` e `src/api/schema.d.ts` | `just lint` |
| Prettier | frontend | `.prettierrc` + `prettier-plugin-tailwindcss` | `just format` |
| tsc | frontend | `tsconfig.json` com `strict: true`, `noUncheckedIndexedAccess: true` | `just typecheck` |
| gitleaks | repo | via pre-commit e CI | — |
| EditorConfig | repo | `.editorconfig`: UTF-8, LF, final newline, indent 4 (py) / 2 (ts, json, yaml, md) | — |
| `.gitattributes` | repo | `* text=auto eol=lf`; binários marcados (`*.png binary`) | — |

### 9.2 Pre-commit (`.pre-commit-config.yaml`)

Executado com `uvx pre-commit` (instalado nos hooks por `just setup`). Apenas hooks rápidos:

- `pre-commit-hooks`: `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-merge-conflict`, `check-added-large-files`, `mixed-line-ending --fix=lf`.
- `ruff-pre-commit`: `ruff check --fix` e `ruff format` em `backend/`.
- Hook local: ESLint e Prettier nos arquivos staged de `frontend/` (via `pnpm --dir frontend exec ...`).
- `gitleaks`: detecção de segredos.

Sem hook `commit-msg`: com squash merge, só o título do PR chega à `main` (seção 4.3).

mypy, tsc e testes rodam **somente no CI** (e localmente via `just`), para não tornar o commit lento.

---

## 10. Estratégia de testes

**Regra geral**: nenhum teste chama serviço externo pago; todo provedor externo tem fake. Lógica temporal usa `Clock` injetável.

### 10.1 Backend

| Tipo | Pasta | Marker | O que cobre | Banco | Externos |
|---|---|---|---|---|---|
| Unitário | `tests/unit/` | `unit` | Regras puras de domínio, com fakes de ports (`Clock`) | Não | Fakes |
| Integração | `tests/integration/` | `integration` | Migrações (upgrade/downgrade), constraints e, quando existirem, repositórios SQL | Postgres real | — |
| API (e2e de endpoint) | `tests/api/` | `api` | App completo via `httpx.AsyncClient(transport=ASGITransport(app))`: status codes, cookies, auth, CSRF, contrato | Postgres real | Fakes via `dependency_overrides` |

**Infraestrutura de banco nos testes**:

- `testcontainers` sobe `postgres:18-alpine` (mesma imagem da produção) uma vez por sessão de testes (fixture `scope="session"`).
- `alembic upgrade head` roda uma vez por sessão contra o container, o que também testa as migrações.
- Cada teste roda dentro de uma transação externa com rollback ao final (`AsyncSession(bind=connection, join_transaction_mode="create_savepoint")`); o provider de sessão da app é sobrescrito para usar essa conexão nos testes de API.
- Requer Docker disponível (WSL local e GitHub Actions `ubuntu-latest`).

**Configuração** (`pyproject.toml`): `asyncio_mode = "auto"`, markers registrados, `--strict-markers`, cobertura com `pytest-cov` (relatório no CI, **sem gate de percentual na E0**).

**Nomenclatura**: arquivos `test_<unidade>.py`; funções `test_<comportamento_esperado>` (ex.: `test_expired_session_returns_401`).

**Testes mínimos da E0**:

- unit: regra de expiração/renovação de sessão (função pura de `domain/auth.py`) com `FakeClock`.
- integration: migração aplica e reverte (`downgrade base`) sem erro; `uq_users_email` rejeita e-mail duplicado.
- api: `GET /health` 200; login com senha correta → cookie → `GET /auth/me` 200; senha incorreta e usuário inexistente → mesma resposta genérica; logout → `/auth/me` 401; `POST` sem `Origin` válido → 403; rate limit do login.

**Factories de dados**: adiadas até existirem entidades de domínio (E1+).

### 10.2 Frontend

| Tipo | Ferramenta | Local | O que cobre |
|---|---|---|---|
| Componente/hook | Vitest + Testing Library (jsdom) | `*.test.tsx` ao lado do arquivo | Renderização, interação, estados de loading/erro |
| Mock de API | MSW + `openapi-msw` | `src/test/handlers.ts` | Respostas tipadas pelo schema |
| E2E | Playwright | `frontend/e2e/` | **Adiado para a E1** (primeiro fluxo real) |

**Testes mínimos da E0**: `LoginForm` (envio, erro de credenciais); `HealthStatus` (sucesso e falha com MSW).

### 10.3 Smoke test de produção

Após cada deploy: `curl -fsS https://<APP_DOMAIN>/api/v1/health` com retries (seção 12.2).

### 10.4 Como executar

| Comando | Executa |
|---|---|
| `just test` | Todos os testes (backend + frontend) |
| `just test-unit` | `pytest -m unit` (rápido, sem Docker) |
| `just test-integration` | `pytest -m integration` |
| `just test-api` | `pytest -m api` |
| `just test-frontend` | `pnpm test` (Vitest, modo run) |

---

## 11. Docker e deploy

Princípios: imagens com versão fixada (nunca `:latest`), multi-stage, usuário não-root, nenhum segredo em imagem (`ARG`/`ENV`), `.dockerignore` por imagem, build `linux/amd64`.

### 11.1 Imagem `api` (`backend/Dockerfile`)

```
stage builder: python:3.14-slim
  COPY --from=ghcr.io/astral-sh/uv:<versão fixa> /uv /bin/uv
  ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
  COPY pyproject.toml uv.lock ./
  RUN uv sync --frozen --no-dev --no-install-project      # camada de dependências (cache)
  COPY app/ migrations/ alembic.ini ./
  RUN uv sync --frozen --no-dev

stage runtime: python:3.14-slim
  usuário app (uid 1000)
  COPY --from=builder /app /app   (inclui .venv)
  ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
  USER app
  EXPOSE 8000
  HEALTHCHECK: python -c "urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health')"
  CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000",
       "--proxy-headers", "--forwarded-allow-ips", "*"]   # ver nota
```

- Base `slim` (Debian/glibc), não Alpine: libs nativas (psycopg, futuramente spaCy) usam wheels prontos.
- **Nota sobre `--forwarded-allow-ips`**: a API só é alcançável pela rede interna do Compose (não publica portas), então confiar nos headers do Caddy é seguro; se possível, restringir à sub-rede da rede interna.
- A mesma imagem executa: API (CMD padrão), `migrate` (`alembic upgrade head`), CLI (`python -m app.cli ...`) e, a partir da E2, o worker.
- `ffmpeg` e outras dependências de sistema entram apenas quando uma entrega precisar.
- `.dockerignore`: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `tests/`, `.env*`, `htmlcov/`, `.coverage`.

### 11.2 Imagem `web` (`frontend/Dockerfile`)

```
stage build: node:26-slim
  instalar pnpm (versão do packageManager)
  COPY package.json pnpm-lock.yaml ./
  RUN pnpm install --frozen-lockfile                      # camada de dependências (cache)
  COPY . .
  RUN pnpm build                                          # → dist/

stage runtime: caddy:2.<x>-alpine
  COPY Caddyfile /etc/caddy/Caddyfile
  COPY --from=build /app/dist /srv
  EXPOSE 80 443 443/udp
```

- Rodar o Caddy como usuário não-root se o binário oficial mantiver a capability `cap_net_bind_service` (validar na implementação); senão, manter o usuário padrão com filesystem read-only onde possível.
- `.dockerignore`: `node_modules/`, `dist/`, `coverage/`, `.env*`, `e2e/`.

**Caddyfile** (referência):

```caddyfile
{$APP_DOMAIN} {
    encode zstd gzip

    handle /api/* {
        reverse_proxy api:8000
    }

    handle {
        root * /srv
        try_files {path} /index.html
        file_server
    }

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options "nosniff"
        Referrer-Policy "strict-origin-when-cross-origin"
        Permissions-Policy "microphone=(self), camera=()"
        -Server
    }

    @immutable path /assets/*
    header @immutable Cache-Control "public, max-age=31536000, immutable"
    @revalidate not path /assets/*
    header @revalidate ?Cache-Control "no-cache"
}
```

> O `header` roda antes do `try_files`: um matcher `path /index.html` não pegaria as navegações da SPA (`/`, `/login`...), que recebem o `index.html` por reescrita. Por isso tudo que não é `/assets/*` revalida; o `?` só define o header se a resposta (ex.: da `api`) não tiver um.


### 11.3 `compose.yaml` (desenvolvimento)

- Serviço único `db`: `postgres:18-alpine` (minor fixada), `ports: "127.0.0.1:5432:5432"`, volume nomeado `db_data` montado em **`/var/lib/postgresql`** (layout do Postgres 18+), `healthcheck` com `pg_isready`, credenciais do `.env`.
- Backend e frontend rodam nativos (`just dev`), com hot reload.

### 11.4 `deploy/compose.prod.yaml` (produção)

| Serviço | Imagem | Detalhes |
|---|---|---|
| `db` | `postgres:18-alpine` (minor fixada) | Volume `db_data:/var/lib/postgresql`; `POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password`; healthcheck `pg_isready`; sem `ports`. |
| `migrate` | `ghcr.io/sgabriel-santos/vocab-api:${IMAGE_TAG}` | `command: alembic upgrade head`; `restart: "no"`; `depends_on: db (service_healthy)`. |
| `api` | `ghcr.io/sgabriel-santos/vocab-api:${IMAGE_TAG}` | `depends_on: db (service_healthy), migrate (service_completed_successfully)`; `env_file: ../.env`; secret `postgres_password`; sem `ports`. |
| `web` | `ghcr.io/sgabriel-santos/vocab-web:${IMAGE_TAG}` | `ports: 80:80, 443:443, 443:443/udp`; volumes `caddy_data:/data`, `caddy_config:/config` (**obrigatórios**: preservam certificados); `APP_DOMAIN` do `.env`; `depends_on: api`. |

Comum a todos: `restart: unless-stopped` (exceto `migrate`), logging `json-file` com `max-size: 10m`, `max-file: "3"`, rede interna única; **nunca** montar `/var/run/docker.sock`.

Limites (`deploy.resources.limits`): `api` 1 CPU / 1 GB; `db` 1 CPU / 1 GB; `web` 0.5 CPU / 256 MB; `migrate` 0.5 CPU / 512 MB.

Volumes nomeados: `db_data`, `caddy_data`, `caddy_config`. Secrets: `postgres_password: file: ./secrets/postgres_password`.

### 11.5 Layout no VPS

```
/opt/vocab/
├── .env                       # Configuração de produção (chmod 600, não versionado)
├── current_tag                # SHA em produção (escrito pelo deploy.sh; referência para rollback manual)
└── deploy/                    # Copiado do repositório a cada deploy
    ├── compose.prod.yaml
    ├── deploy.sh
    ├── backup.sh              # (E1)
    ├── systemd/               # (E1)
    └── secrets/postgres_password   # Criado manualmente no setup (chmod 600)
```

### 11.6 Setup inicial do VPS (runbook em `deploy/README.md`)

1. Criar o VPS com Ubuntu 24.04 LTS (sem painel), cadastrando a chave SSH pessoal.
2. Hardening: usuário administrativo com sudo, `PasswordAuthentication no`, `PermitRootLogin no`; `ufw` (ou firewall do provedor) liberando 22, 80, 443/tcp e 443/udp; `unattended-upgrades` ativo.
3. Instalar Docker Engine + plugin Compose (repositório oficial da Docker).
4. Criar usuário `deploy` (grupo `docker`, **sem sudo**), com a chave pública de deploy em `authorized_keys` (opções `no-port-forwarding,no-agent-forwarding,no-X11-forwarding`). Não usar `command=`: o CI copia `deploy/` a cada deploy (o que um comando forçado bloquearia) e o grupo `docker` já equivale a root no host, então a restrição não protegeria nada. A proteção está no acesso à chave (seção 12.2). O `deploy.sh` valida o SHA recebido (`^[0-9a-f]{40}$`).
5. Criar `/opt/vocab/.env` (`chmod 600`) e `/opt/vocab/deploy/secrets/postgres_password` (senha forte, `chmod 444`, dentro de `secrets/` com `chmod 700` e dono `deploy`; ver 5.4).
6. DNS no Registro.br: registro `A` `vocab` → IP do VPS (e `AAAA` se houver IPv6).
7. Primeiro deploy via GitHub Actions; criar o usuário com `create-user`.
8. **Na E1:** configurar o backup (11.7) e testar um restore.

### 11.7 Backup e restore (entra na E1)

> Não faz parte da E0: até a E1 o banco contém apenas o usuário criado pela CLI, recriável em segundos. O backup é **critério de pronto da E1** e precisa estar funcionando antes de importar a lista real de termos. O desenho abaixo já está decidido (ADR 0002).

- `deploy/backup.sh`, executado diariamente por `vocab-backup.timer` (systemd, no host):
  1. `docker compose -f compose.prod.yaml exec -T db pg_dump -U <user> -Fc <db>`
  2. Criptografa com `age` (chave pública no VPS; chave privada guardada **fora** do VPS).
  3. Envia com `rclone` para o bucket B2/R2 (`vocab-backups/<data>.dump.age`).
  4. Retenção: diários dos últimos 14 dias + mensais dos últimos 6 meses (limpeza no próprio script ou lifecycle do bucket).
  5. Ping no Healthchecks.io ao concluir (alerta se não houver ping).
- Credenciais do `rclone` ficam em `~deploy/.config/rclone/rclone.conf` (`chmod 600`).
- **Restore** (documentado em `deploy/README.md`): baixar → `age -d` → `pg_restore --clean --if-exists` em um banco vazio. Testar o restore uma vez no setup e sempre que o procedimento mudar.

---

## 12. CI/CD

GitHub Actions. Actions com versão fixada (tag maior ou SHA), `permissions` mínimas por job. Os jobs chamam as receitas do `justfile`, então o CI executa o mesmo que o desenvolvedor executa localmente.

### 12.1 `ci.yml`: em todo PR e push fora da `main`

Gatilhos: `pull_request`, `push` (exceto `main`) e `workflow_call` (para ser reutilizado pelo `deploy.yml`).

| Job | Passos |
|---|---|
| `backend` | checkout → `astral-sh/setup-uv` (versão fixa, cache) → `uv sync --frozen` → `just lint-backend` → `just typecheck-backend` → `just test-backend` (unit + integration + api, testcontainers usa o Docker do runner) → cobertura como artefato |
| `frontend` | checkout → `pnpm/action-setup` → `actions/setup-node` (`node-version-file: frontend/.nvmrc`, cache pnpm) → `pnpm install --frozen-lockfile` → `just lint-frontend` → `just typecheck-frontend` → `just test-frontend` → `just build-frontend` |
| `contract` | setup uv + pnpm → `just gen-client` → `git diff --exit-code frontend/src/api/` (falha se o client estiver desatualizado) |
| `secrets` | `gitleaks` no diff/histórico do push |

`just` é instalado no CI com `extractions/setup-just` (ou `uv tool install rust-just`). Os nomes exatos das receitas seguem a seção 13.

### 12.2 `deploy.yml`: push na `main`

Gatilhos: `push` na `main` e `workflow_dispatch` (input `sha`, para reimplantar uma tag existente). Um único workflow com jobs encadeados por `needs` (sem `workflow_run`, que sempre executa a versão do workflow da `main` e é mais difícil de depurar). `concurrency: { group: production, cancel-in-progress: false }`. `environment: production` nos jobs de deploy.

0. **ci**: `uses: ./.github/workflows/ci.yml` (mesmos jobs do PR). Pulado no `workflow_dispatch`.
1. **build-and-push** (`needs: ci`; pulado no `workflow_dispatch`, que reutiliza imagens já publicadas) (`permissions: contents: read, packages: write`): `docker/setup-buildx-action` → `docker/login-action` (GHCR, `GITHUB_TOKEN`) → `docker/build-push-action` para `vocab-api:<sha>` e `vocab-web:<sha>`, `platforms: linux/amd64`, cache `type=gha`.
2. **deploy**:
   - Configura a chave SSH e o `known_hosts` (do Environment; nunca `StrictHostKeyChecking=no`).
   - Copia `deploy/` para `/opt/vocab/deploy/` com `rsync` (sem `secrets/`, que existe só no VPS).
   - Executa via SSH `/opt/vocab/deploy/deploy.sh <sha>`, enviando o `GITHUB_TOKEN` efêmero pelo stdin para `docker login ghcr.io`.
3. **`deploy.sh <sha>`** (no VPS):
   1. Valida o SHA; `docker login ghcr.io --password-stdin`.
   2. `IMAGE_TAG=<sha> docker compose -f compose.prod.yaml pull`.
   3. `IMAGE_TAG=<sha> docker compose -f compose.prod.yaml up -d --remove-orphans` (o `migrate` roda antes da `api` pelo `depends_on`).
   4. Smoke test: `curl -fsS https://$APP_DOMAIN/api/v1/health` com até ~10 tentativas espaçadas.
   5. Sucesso → grava `current_tag=<sha>`, `docker image prune` de imagens antigas (mantendo as duas mais recentes), `docker logout`.
   6. Falha → sai com erro (job vermelho) e **não** grava `current_tag`. Não há rollback automático: projeto single-user, alguns minutos fora do ar são aceitáveis.

**Secrets do Environment `production`**: `DEPLOY_HOST`, `DEPLOY_USER` (`deploy`), `DEPLOY_SSH_KEY` (chave privada exclusiva do deploy), `DEPLOY_KNOWN_HOSTS`. Variável: `APP_DOMAIN`.

**Proteção da chave de deploy**: o usuário `deploy` está no grupo `docker` e recebe o compose do CI, então a chave vazada equivale a acesso root ao VPS. Por isso o Environment `production` tem *deployment branch rule* restrita à `main` (workflows de PRs e outras branches não acessam a chave), a chave é exclusiva do deploy e revogável a qualquer momento removendo-a do `authorized_keys`.

**Rollback manual**: `just deploy-rollback <sha>` dispara o `deploy.yml` (`workflow_dispatch` com input `sha`), que pula CI e build e executa `deploy.sh <sha>` com uma tag já publicada (ex.: a anterior, visível no histórico de deploys do GitHub). Se a versão com falha aplicou uma migração incompatível, rodar antes o downgrade **com a imagem da versão com falha**, que é a que conhece a migração nova (`IMAGE_TAG=<sha com falha> docker compose -f compose.prod.yaml run --rm migrate alembic downgrade <revisão>`). Rollback automático pode ser reavaliado quando houver dados ou uso que justifiquem.

### 12.3 Dependabot (`.github/dependabot.yml`)

**Mensal**, PRs agrupados por ecossistema (menos ruído em um projeto solo onde todo PR passa pelo CI): `github-actions` (raiz), `uv` (`/backend`), `npm` (`/frontend`, funciona com pnpm), `docker` (`/backend`, `/frontend`). PRs passam pelo CI como qualquer outro.

### 12.4 Proteção da `main` (configuração no GitHub)

Ruleset: bloquear push direto e force push, exigir PR, exigir status checks `backend`, `frontend`, `contract`, `secrets`, exigir histórico linear; merge permitido apenas por squash.

---

## 13. Comandos essenciais

Todos via `just` (instalação: `uv tool install rust-just`). `just --list` mostra as receitas com descrição. O `justfile` carrega o `.env` (`set dotenv-load`).

| Receita | O que faz |
|---|---|
| `just setup` | Instala deps do backend (`uv sync`) e do frontend (`pnpm install`), instala os hooks (`uvx pre-commit install --install-hooks`) e copia `.env.example` → `.env` se não existir. |
| `just db-up` / `just db-down` | Sobe/derruba o Postgres do `compose.yaml`. |
| `just dev` | `db-up` + backend (`uvicorn --reload` na 8000) + frontend (`pnpm dev` na 5173) em paralelo. |
| `just dev-backend` / `just dev-frontend` | Apenas backend / apenas frontend. |
| `just migrate` | `alembic upgrade head` no banco local. |
| `just migration "msg"` | `alembic revision --autogenerate -m "msg"` (revisar o arquivo gerado). |
| `just create-user <email>` | Cria usuário (senha via prompt). |
| `just seed` | `python -m app.cli seed-dev`: cria o usuário de desenvolvimento (`SEED_USER_*`); idempotente e recusado em produção. |
| `just lint` | `lint-backend` (ruff check + ruff format --check) + `lint-frontend` (eslint + prettier --check). |
| `just format` | `ruff format` + `ruff check --fix` + `prettier --write`. |
| `just typecheck` | `typecheck-backend` (mypy) + `typecheck-frontend` (tsc --noEmit). |
| `just test` | Todos os testes (backend + frontend). |
| `just test-unit` / `just test-integration` / `just test-api` | Testes do backend por marker. |
| `just test-backend` | `pytest` com todos os markers + cobertura (usado no CI). |
| `just test-frontend` | Vitest (run). |
| `just gen-client` | Exporta o OpenAPI (`uv run python -m app.scripts.export_openapi`) para um arquivo temporário e gera `frontend/src/api/schema.d.ts` com `openapi-typescript`. O JSON intermediário não é versionado. |
| `just build` | `build-frontend` (Vite) + build local das imagens Docker. |
| `just deploy-rollback <sha>` | Rollback manual: dispara o `deploy.yml` para reimplantar uma tag já publicada (`gh workflow run deploy.yml -f sha=<sha>`). |

---

## 14. Critério de pronto da E0

- `just setup && just dev` sobe o ambiente local; login funciona em `http://localhost:5173`.
- `just lint`, `just typecheck` e `just test` passam localmente e no CI.
- A URL pública `https://vocab.<domínio>` abre no celular com HTTPS válido; a PWA instala.
- Login com o usuário criado via CLI funciona; a tela protegida exibe o status do backend; logout funciona.
- Um merge na `main` publica automaticamente; um deploy com smoke test falhando deixa o job vermelho; `just deploy-rollback <sha>` reimplanta uma tag anterior.
- Nenhum segredo no repositório (gitleaks verde); o `.env.example` documenta todas as variáveis.
