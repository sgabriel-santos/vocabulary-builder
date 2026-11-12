# AGENTS.md

Instruções para agentes de IA que trabalham neste repositório. Este é o documento **canônico**; o `CLAUDE.md` o importa.

## Projeto

**Vocabulary Builder**: PWA de uso pessoal (single-user, com `user_id` no modelo para não bloquear multiusuário) que transforma palavras e expressões em inglês anotadas pelo usuário em vocabulário ativo: captura, enriquecimento por IA, repetição espaçada (FSRS), pronúncia, diário e estúdio de vídeo.

Leia antes de começar:

| Documento | Conteúdo |
|---|---|
| [`docs/project-overview.md`](docs/project-overview.md) | Visão, escopo (`F-xx`), domínio, arquitetura, roadmap, questões em aberto |
| [`docs/delivery-plan.md`](docs/delivery-plan.md) | Entregas E0–E5 (fatias verticais, cada uma termina em deploy) |
| [`docs/scaffolding-specification.md`](docs/scaffolding-specification.md) | Especificação completa do scaffolding: estrutura, stack, convenções, testes, Docker, CI/CD, comandos |
| [`docs/adr/`](docs/adr/README.md) | Decisões arquiteturais (ADRs) |

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python **3.14**, **uv**, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2.0 async, **psycopg 3**, Alembic, structlog, argon2-cffi |
| Frontend | Node **26 LTS**, **pnpm**, React + TypeScript (strict) + Vite, **TanStack Router** (rotas por arquivo), TanStack Query, openapi-fetch + openapi-react-query, Tailwind CSS v4 + shadcn/ui, vite-plugin-pwa |
| Banco | PostgreSQL **18** |
| Qualidade | Ruff, mypy (strict), pytest + pytest-asyncio + testcontainers, ESLint (flat) + Prettier, Vitest + Testing Library + MSW, pre-commit, gitleaks |
| Infra | Docker Compose, Caddy, VPS (Hostinger), GHCR, GitHub Actions, `just` |

Versões exatas ficam nos lockfiles (`backend/uv.lock`, `frontend/pnpm-lock.yaml`) e nas tags das imagens. **Verifique a documentação atual** de bibliotecas e APIs externas antes de usá-las; não confie apenas em conhecimento prévio.

## Onde cada coisa vive

| O quê | Onde |
|---|---|
| Rotas HTTP e schemas de request/response | `backend/app/api/v1/` (`schemas/`) |
| Entidades e regras de negócio puras | `backend/app/domain/` |
| Casos de uso | `backend/app/application/` |
| Interfaces (Protocol) de provedores e repositórios | `backend/app/ports/` |
| Implementações (banco, segurança, provedores externos) | `backend/app/adapters/` (`db/models/`, `db/repositories/`, `security/`, ...) |
| Config, logging, middlewares, composition root (DI) | `backend/app/core/` |
| CLI administrativa | `backend/app/cli/` |
| Migrações | `backend/migrations/versions/` |
| Testes do backend | `backend/tests/{unit,integration,api,fakes}/` |
| Rotas do frontend (finas) | `frontend/src/routes/` |
| Telas, componentes e hooks por funcionalidade | `frontend/src/features/<feature>/` |
| Client da API (gerado + wrapper) | `frontend/src/api/` |
| Componentes compartilhados / shadcn | `frontend/src/components/` (`ui/`) |
| Arquivos de produção (compose, scripts, runbook) | `deploy/` |
| Workflows | `.github/workflows/` |

Árvore completa: seção 2 da [especificação](docs/scaffolding-specification.md#2-estrutura-de-diretórios).

## Como rodar

Pré-requisitos: Docker, `uv`, Node 26 + pnpm, `just` (`uv tool install rust-just`).

```bash
just setup                 # deps, hooks de pre-commit, .env a partir do .env.example
just dev                   # Postgres (compose) + API :8000 + frontend :5173
just migrate               # aplica migrações no banco local
just create-user <email>   # cria o usuário (senha via prompt)
just lint && just typecheck && just test
just gen-client            # regenera o client da API após mudar rotas/schemas
just --list                # todas as receitas
```

## Convenções obrigatórias

- **Idioma**: código, nomes, tabelas, endpoints, branches e commits em inglês; documentação em pt-BR; interface em pt-BR (texto direto nos componentes, sem i18n).
- **Nomenclatura**: Python `snake_case` (módulos, funções) e `PascalCase` (classes); TS componentes `PascalCase.tsx`, hooks `useX.ts`, demais `kebab-case.ts`; tabelas plural `snake_case`; JSON da API em `snake_case` (sem alias camelCase); endpoints sob `/api/v1`; testes `test_*.py` e `*.test.ts(x)`. Detalhes: seção 4 da especificação.
- **Funcionalidades** são referenciadas pelos códigos `F-xx` em planos, branches, PRs e commits.
- **Git**: branch curta (`feat/F-01-...`, `fix/...`, `chore/...`, `docs/...`) → PR → squash merge na `main`. Nunca push direto na `main`. Commits seguem o `CLAUDE.md` (Conventional Commits em inglês, sem atribuição de IA, aprovação explícita do usuário antes de cada commit).
- **Banco**: toda mudança de schema por migração Alembic revisada à mão; **prefira** migrações compatíveis com a versão anterior (diretriz, não regra: o rollback é manual e não reverte schema; ver spec §4.4). Timestamps em UTC.
- **ADRs**: decisões arquiteturais novas viram `docs/adr/NNNN-titulo.md`.

## Faça

- Coloque regras de negócio em `domain/`/`application/`, nunca em routers.
- Acesse provedores externos **somente via port** e crie o fake correspondente em `backend/tests/fakes/`. Repositórios não precisam de fake em memória (os testes usam Postgres real).
- Use o port `Clock` para qualquer lógica dependente de tempo.
- Escreva testes no nível certo: `unit` (sem banco), `integration` (repositórios/migrações), `api` (endpoints com fakes de provedores).
- Valide toda saída de LLM com Pydantic; prompts versionados em arquivos dedicados (a partir da E2).
- Rode `just gen-client` sempre que alterar rotas ou schemas da API (o CI falha em drift).
- Mantenha `.env.example` atualizado ao adicionar configuração.
- Atualize `docs/project-overview.md` e os ADRs quando uma decisão mudar escopo, arquitetura ou domínio.

## Não faça

- Não implemente funcionalidades de fases/entregas futuras sem pedido explícito.
- Não decida questões listadas como "em aberto" (overview §15) sem confirmar com o usuário.
- Não exponha segredos: nada de chaves em código, imagens Docker (`ARG`/`ENV`), frontend ou logs. Segredos de produção vivem em `/run/secrets` no VPS.
- Não chame APIs pagas reais em testes automatizados.
- Não armazene tokens de autenticação no `localStorage`/`sessionStorage`; a sessão é um cookie `HttpOnly` gerenciado pelo backend.
- Não exponha modelos SQLAlchemy na camada `api/` nem retorne-os diretamente.
- Não edite à mão arquivos gerados: `frontend/src/routeTree.gen.ts`, `frontend/src/api/openapi.json`, `frontend/src/api/schema.d.ts`.
- Não publique portas de serviços além do `web` (Caddy) no compose de produção; não monte `/var/run/docker.sock` em containers.
- Não use tags `latest` de imagens.
- Não adicione cache de `/api/*` no service worker (offline está fora do escopo).
- Não introduza infraestrutura ou abstrações sem um problema real presente (projeto pessoal, single-user).

## Decisões arquiteturais (não contornar)

| Decisão | Motivo | ADR |
|---|---|---|
| VPS + Docker Compose + Caddy; frontend e API na mesma origem | Custo fixo baixo, sem cold start, sem CORS | [0001](docs/adr/0001-hosting-vps-compose-caddy.md) |
| Postgres em container no VPS + backup criptografado externo (a partir da E1) | Latência mínima; backup diário cobre o risco | [0002](docs/adr/0002-postgres-on-vps-with-offsite-backup.md) |
| Senha (Argon2) + sessão server-side em cookie; sem JWT | Revogação imediata, imune a roubo por XSS, funciona na PWA do iOS | [0003](docs/adr/0003-auth-password-server-side-sessions.md) |
| uv + Python 3.14 | Velocidade e reprodutibilidade; 3.15 bloqueado pelo spaCy | [0004](docs/adr/0004-python-tooling-uv-python-314.md) |
| pnpm + Node 26 LTS | Instalação rápida e estrita | [0005](docs/adr/0005-frontend-tooling-pnpm-node-26.md) |
| SQLAlchemy 2.0 async + psycopg 3; domínio separado onde há regra | Domínio testável sem banco, sem cerimônia em leituras simples | [0006](docs/adr/0006-persistence-sqlalchemy-psycopg-domain-separation.md) |
| Testes unit/integration/api + fakes; Postgres via testcontainers | Mesmo comportamento local e no CI | [0007](docs/adr/0007-backend-testing-testcontainers.md) |
| TanStack Router com rotas por arquivo | Rotas e search params tipados | [0008](docs/adr/0008-frontend-routing-tanstack-router.md) |
| Client OpenAPI gerado (só tipos) e versionado, com checagem de drift | Contrato quebra na compilação, não em produção | [0009](docs/adr/0009-api-client-openapi-fetch-versioned.md) |
| Imagens `api` e `web`; compose dev/prod separados; migração one-off | Uma imagem para API/migrate/CLI/worker; deploy seguro | [0010](docs/adr/0010-docker-images-and-compose-layout.md) |
| Deploy automático na `main` com smoke test; rollback manual | `main` = produção; sem o custo de expand/contract obrigatório | [0011](docs/adr/0011-ci-cd-auto-deploy-with-rollback.md) |
| PR + squash merge; `main` protegida | `main` sempre verde; PR como ponto de revisão | [0012](docs/adr/0012-branching-pr-squash-merge.md) |

Se uma dessas decisões parecer inadequada para uma tarefa, **pare e consulte o usuário** em vez de contorná-la.
