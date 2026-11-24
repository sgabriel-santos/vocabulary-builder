# Blueprint de Desenvolvimento — E0 (walking skeleton)

> **Status:** aprovado · **Data:** 2026-11-12
> **Origem:** [`scaffolding-specification.md`](scaffolding-specification.md) (2ª revisão) e ADRs [0001–0012](adr/README.md).
> **Uso:** handoff para a sessão de implementação. Este documento é autocontido: quem o executa não precisa ler a spec. Em caso de conflito, a spec e os ADRs prevalecem; depois que os arquivos reais existirem, eles prevalecem sobre os trechos deste documento.

## Sumário

0. [Contexto do projeto](#0-contexto-do-projeto)
1. [Visão geral do plano](#1-visão-geral-do-plano)
2. [Implementação da entidade de exemplo](#2-implementação-da-entidade-de-exemplo)
3. [Plano de seed](#3-plano-de-seed)
4. [Plano de testes](#4-plano-de-testes)
5. [Sequência de implementação](#5-sequência-de-implementação)
6. [Pontos de atenção](#6-pontos-de-atenção)
7. [Sessões e progresso](#7-sessões-e-progresso)

---

## 0. Contexto do projeto

### 0.1 O que é

**Vocabulary Builder**: PWA de uso pessoal, single-user (com `user_id` no modelo para não bloquear multiusuário), para transformar palavras em inglês anotadas pelo usuário em vocabulário ativo. É um **projeto pessoal de aprendizado de inglês**, não um trabalho acadêmico: arquitetura e infraestrutura se justificam pelo uso real.

A **E0** não entrega nenhuma funcionalidade `F-xx`. Ela entrega o caminho completo do código até a produção: backend, frontend, autenticação, testes, CI e deploy automático em um VPS com HTTPS.

### 0.2 Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python **3.14**, **uv**, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2.0 async, **psycopg 3** (único driver), Alembic, structlog, argon2-cffi |
| Frontend | Node **26 LTS**, **pnpm**, React + TypeScript (strict) + Vite, TanStack Router (rotas por arquivo), TanStack Query, openapi-fetch + openapi-react-query, Tailwind CSS v4 + shadcn/ui, vite-plugin-pwa |
| Banco | PostgreSQL **18** (`postgres:18-alpine`, minor fixada) em dev, testes e produção |
| Qualidade | Ruff, mypy strict, pytest + pytest-asyncio + pytest-cov + testcontainers, ESLint flat + Prettier, Vitest + Testing Library + MSW + openapi-msw, pre-commit, gitleaks |
| Infra | Docker Compose, Caddy 2, VPS Hostinger KVM 2 (Ubuntu 24.04), GHCR, GitHub Actions, `just` |

Regra geral: **verifique a documentação atual** de cada biblioteca antes de usar (APIs de config mudam entre versões); fixe versões nos lockfiles, nas tags de imagem e nas actions. Nunca use tag `latest`.

### 0.3 Convenções obrigatórias

- **Idioma**: código, nomes, tabelas, endpoints, branches e commits em inglês; documentação e comentários em pt-BR; textos da interface em pt-BR, direto nos componentes (sem i18n).
- **Python**: módulos e funções `snake_case`, classes `PascalCase`. Ports sem prefixo `I` (`Clock`, `PasswordHasher`); adapters tecnologia + papel (`SystemClock`, `Argon2PasswordHasher`); fakes `Fake` + papel (`FakeClock`).
- **TS**: componentes `PascalCase.tsx`, hooks `useX.ts`, demais `kebab-case.ts`; testes `*.test.ts(x)` ao lado do arquivo.
- **Banco**: tabelas plural `snake_case`; FKs `<entidade>_id`; timestamps `*_at` em `timestamptz` (UTC); IDs UUID gerados na aplicação (`uuid.uuid7()`, disponível no Python 3.14); constraints com nomes da convenção do `MetaData` (`pk_`, `fk_`, `uq_`, `ix_`, `ck_`).
- **API**: prefixo `/api/v1`; JSON em `snake_case` (sem alias camelCase); operationId `<tag>-<nome da função>`; erros no formato padrão do FastAPI (`{"detail": ...}`); nunca retornar modelos ORM.
- **Git**: branch curta → PR → squash merge na `main`. Commits em Conventional Commits, inglês, **sem atribuição de IA**, e **aprovação explícita do usuário antes de cada commit** (regras completas no `CLAUDE.md`).
- **Segredos**: nunca no código, em imagens (`ARG`/`ENV`), no frontend ou em logs. Em produção ficam em `/run/secrets`.
- **Arquivos gerados** (nunca editar à mão): `frontend/src/routeTree.gen.ts`, `frontend/src/api/schema.d.ts`.

### 0.4 Arquitetura do backend (camadas)

| Camada | Responsabilidade | Pode depender de | Não pode depender de |
|---|---|---|---|
| `app/domain/` | Regras puras (dataclasses e funções) | biblioteca padrão | FastAPI, SQLAlchemy, Pydantic, adapters |
| `app/application/` | Casos de uso | `domain/`, `ports/`, modelos ORM e `AsyncSession` (CRUD e leituras simples) | `api/`, adapters concretos de provedores |
| `app/ports/` | Interfaces (`typing.Protocol`) | `domain/` | adapters |
| `app/adapters/` | Implementações (banco, segurança) | `ports/`, `domain/`, libs externas | `api/` |
| `app/api/` | Routers e schemas HTTP | `application/`, `core/`, schemas | adapters concretos (recebe via DI) |
| `app/core/` | Config, logging, middleware, composition root | tudo | — |

- **Sem ports de repositório na E0**: `users` e `sessions` são CRUD sem regra; os casos de uso usam a `AsyncSession` diretamente. Repositório (port + `adapters/db/repositories/`) só nasce com o primeiro agregado com regra de negócio (E3).
- DI com `Depends` do FastAPI; providers em `core/container.py`; testes trocam providers com `app.dependency_overrides`. Sem biblioteca de container.

### 0.5 Topologia de produção

```
Internet ──HTTPS──▶ web (Caddy + SPA) :80 :443 :443/udp   ← único serviço com portas
                     ├── /api/*  → reverse_proxy api:8000
                     └── /*      → arquivos estáticos (fallback index.html)
                    api (FastAPI/uvicorn) ──▶ db (postgres:18, volume db_data)
                    migrate (one-off: alembic upgrade head, roda antes da api)
```

Frontend e API na **mesma origem** (`vocab.<domínio>`): sem CORS, cookie `SameSite=Lax` simples. Em dev, o Vite faz proxy de `/api` para `localhost:8000`, reproduzindo a mesma origem.

### 0.6 Ambiente local verificado (2026-11-12)

| Ferramenta | Situação | Ação |
|---|---|---|
| uv | 0.12.13 instalado | — |
| Docker | 29.4.3 instalado | — |
| Node | **v24.18.0** (spec exige 26) | Instalar Node 26 (T-01) |
| pnpm | **ausente** | Instalar standalone (T-01) |
| just | **ausente** | `uv tool install rust-just` (T-01) |
| gh | **ausente** | Opcional: só para `just deploy-rollback` (alternativa: UI do GitHub) |

Remote: `https://github.com/sgabriel-santos/vocabulary-builder.git`. Infra de produção: **VPS contratado e domínio registrado**, ainda sem configuração (hardening, Docker, usuário `deploy`, DNS).

---

## 1. Visão geral do plano

### 1.1 O que será implementado

| Parte | Propósito |
|---|---|
| Base do repositório (raiz, `justfile`, `compose.yaml`) | Ponto de entrada único de comandos e Postgres local |
| Backend em camadas + `GET /api/v1/health` | Prova que API e banco estão vivos (usado no smoke test) |
| **Entidade de exemplo: `User` + `Session` (autenticação)** | Atravessa todas as fronteiras: migração → modelos ORM → domínio puro → casos de uso → API → client gerado → telas |
| CLI `create-user` e `seed-dev` | Único jeito de criar usuários (sem cadastro público) e seed do ambiente de dev |
| Frontend (login, área protegida, status do backend, PWA) | Prova do fluxo no navegador e da instalação no celular |
| Testes unit / integration / api / componente | Template para todas as features futuras |
| Pre-commit e CI | `main` sempre verde; drift do contrato detectado |
| Imagens Docker, compose de produção, VPS, deploy e rollback | Caminho do merge até a produção |

**Por que `User` + `Session`**: é o escopo já previsto da E0, é pequeno, e exercita tudo o que as features futuras vão usar: migração Alembic, modelos tipados, regra pura testável com relógio injetável (expiração deslizante), caso de uso com port (`PasswordHasher`, `Clock`), endpoint com cookie e CSRF, client gerado e rota protegida. Usar `Term` anteciparia a E1.

### 1.2 Fora do escopo

Qualquer `F-xx`; fila/worker; Redis; object storage; ports de provedores de IA; repositórios (port + adapter SQL); Playwright (E1); factories de dados; backup externo (E1); rollback automático; `just prod-local`; hook `commit-msg`; TOTP e tela de sessões ativas; colunas `display_name`/`settings` em `users` e `user_agent` em `sessions`.

### 1.3 Critérios de sucesso (critério de pronto da E0)

1. `just setup && just dev` sobe o ambiente; após `just migrate && just seed`, o login com `dev@example.com` funciona em `http://localhost:5173`.
2. `just lint`, `just typecheck` e `just test` passam localmente e no CI.
3. `https://vocab.<domínio>` abre no celular com HTTPS válido e a PWA instala (Android e iOS).
4. Login com o usuário criado pela CLI em produção funciona; a tela protegida mostra o status da API e do banco; logout funciona.
5. Um merge na `main` publica automaticamente; um deploy com smoke test falhando deixa o job vermelho; `just deploy-rollback <sha>` (ou o `workflow_dispatch` pela UI) reimplanta uma tag anterior.
6. gitleaks verde; `.env.example` documenta todas as variáveis.

---

## 2. Implementação da entidade de exemplo

A ordem segue a de implementação recomendada: **login local de ponta a ponta primeiro, depois deploy, por último o restante do CI/CD**. Os números `T-xx` referem-se à seção 5.

### 2.1 Base do repositório (T-02)

**Onde**: raiz do repositório.

- `README.md`: duas ou três frases sobre o projeto, pré-requisitos e o bloco "Como rodar" (`just setup`, `just dev`, `just migrate`, `just seed`), apontando para `docs/`.
- `.editorconfig`: UTF-8, LF, `insert_final_newline`, indent 4 em `*.py`, 2 em `*.{ts,tsx,js,json,yaml,yml,md,css,html}`.
- `.gitattributes`: `* text=auto eol=lf`; `*.png binary`, `*.ico binary`.
- `.gitignore`: `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `htmlcov/`, `.coverage`, `coverage/`, `node_modules/`, `dist/`, `dev-dist/`, `deploy/secrets/*` (com exceção `!deploy/secrets/.gitkeep`).
- `.env.example` (raiz):

```dotenv
# ---------- Aplicação ----------
APP_ENV=development              # development | test | production
APP_DOMAIN=localhost             # Produção: vocab.<domínio> (Caddy e checagem de Origin)
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

- `compose.yaml` (dev): serviço único `db` com `postgres:18.<minor>-alpine`, `ports: ["127.0.0.1:5432:5432"]`, `environment` com `POSTGRES_DB/USER/PASSWORD` vindos do `.env` (`${POSTGRES_DB}`...), volume nomeado `db_data` montado em **`/var/lib/postgresql`** (layout do Postgres 18+; montar em `/var/lib/postgresql/data` quebra), `healthcheck: pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}`.
- `justfile`: `set dotenv-load` e `set shell := ["bash", "-euo", "pipefail", "-c"]`. Receitas desta etapa: `setup`, `db-up` (`docker compose up -d --wait db`), `db-down` (`docker compose down`). As demais são acrescentadas nas tarefas seguintes; a tabela completa está na seção 4.6.
  - `setup`: `cp -n .env.example .env || true`; `cd backend && uv sync`; `cd frontend && pnpm install`; `uvx pre-commit install --install-hooks` (a partir da T-21).

**Resultado**: `just setup && just db-up` deixa o Postgres saudável em `127.0.0.1:5432`.

### 2.2 Projeto Python (T-03)

**Onde**: `backend/`.

- `backend/.python-version`: `3.14`.
- `backend/pyproject.toml` (PEP 621):
  - `[project]`: `name = "vocab-api"`, `requires-python = ">=3.14,<3.15"`, dependências: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `sqlalchemy[asyncio]`, `psycopg[binary]`, `alembic`, `structlog`, `argon2-cffi`.
  - `[dependency-groups] dev`: `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`, `testcontainers[postgres]`, `ruff`, `mypy`.
  - `[tool.uv] package = false` (é uma aplicação, não uma biblioteca; o código roda a partir de `backend/`).
  - `[tool.ruff]`: `target-version = "py314"`, `line-length = 100`; `[tool.ruff.lint] select = ["E","F","I","B","UP","SIM","ASYNC","S","RUF"]`; `per-file-ignores = { "tests/**" = ["S101", "S105", "S106"] }`.
  - `[tool.mypy]`: `strict = true`, `plugins = ["pydantic.mypy"]`, `files = ["app"]`.
  - `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `pythonpath = ["."]`, `asyncio_mode = "auto"`, escopo de event loop **de sessão** para fixtures e testes (ver 6.2), `markers = ["unit", "integration", "api"]`, `addopts = "--strict-markers"`.
  - `[tool.coverage.run] source = ["app"]`.
- `uv lock` → `backend/uv.lock` versionado.
- Pacotes vazios com `__init__.py`: `app/`, `app/api/`, `app/api/v1/`, `app/api/v1/schemas/`, `app/domain/`, `app/application/`, `app/application/auth/`, `app/ports/`, `app/adapters/`, `app/adapters/security/`, `app/adapters/db/`, `app/adapters/db/models/`, `app/core/`, `app/cli/`, `app/scripts/`; `tests/`, `tests/fakes/`, `tests/unit/`, `tests/integration/`, `tests/api/`.

**Resultado**: `cd backend && uv sync && uv run ruff check && uv run mypy` passam com o projeto vazio.

### 2.3 Núcleo: configuração, logging, app (T-04)

**`app/core/config.py`**

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        secrets_dir="/run/secrets" if Path("/run/secrets").is_dir() else None,
        extra="ignore",
    )
    app_env: Literal["development", "test", "production"] = "development"
    app_domain: str = "localhost"
    log_level: str = "INFO"
    log_format: Literal["console", "json"] = "console"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "vocab"
    postgres_user: str = "vocab"
    postgres_password: SecretStr = SecretStr("vocab")
    session_cookie_name: str = "vocab_session"
    session_ttl_days: int = 60
    session_cookie_secure: bool = False
    login_rate_limit: str = "5/minute"
    seed_user_email: str = "dev@example.com"
    seed_user_password: SecretStr = SecretStr("dev-password-123")
```

- Precedência: variáveis de ambiente > arquivos em `/run/secrets` > defaults. **Não** usar `env_file`: o `justfile` carrega o `.env` (`set dotenv-load`) e, em produção, o Compose injeta `env_file`. Os defaults já servem para dev, então `uv run ...` fora do `just` também funciona.
- Propriedade `database_url`: montar com `sqlalchemy.URL.create("postgresql+psycopg", username=..., password=postgres_password.get_secret_value(), host=..., port=..., database=...)` (escapa caracteres especiais da senha).
- Propriedade `allowed_origins`: em `production`, `[f"https://{app_domain}"]`; caso contrário, `["http://localhost:5173", "http://localhost:8000"]`.
- Propriedade `login_rate_limit_parsed -> tuple[int, int]`: `"5/minute"` → `(5, 60)`; aceitar `second|minute|hour`.
- `model_validator(mode="after")`: em `production`, exigir `session_cookie_secure=True` e `log_format="json"` (falha no boot em vez de rodar inseguro).
- `get_settings()` com `@lru_cache`.

**`app/core/logging.py`**: `configure_logging(settings)` com structlog: processors `merge_contextvars`, `add_log_level`, `TimeStamper(fmt="iso", utc=True)`, e `JSONRenderer()` se `log_format == "json"` senão `ConsoleRenderer()`; nível pelo `log_level`. Redirecionar o logging padrão (uvicorn) para o mesmo formato é desejável, mas não obrigatório na E0.

**`app/core/middleware.py`**: middleware HTTP (`@app.middleware("http")` ou ASGI puro) que:
1. lê `X-Request-ID` do request ou gera `uuid4().hex`;
2. `structlog.contextvars.bind_contextvars(request_id=...)` e limpa ao final;
3. mede a duração e loga `http_request` com `method`, `path` (template da rota quando disponível), `status`, `duration_ms`;
4. devolve `X-Request-ID` no response.
Nunca logar headers `Cookie`/`Set-Cookie` nem corpo de requests de auth.

**`app/main.py`**

```python
def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    app = FastAPI(
        title="Vocabulary Builder API",
        docs_url=None if settings.app_env == "production" else "/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        generate_unique_id_function=lambda route: f"{route.tags[0]}-{route.name}",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.login_rate_limiter = InMemoryRateLimiter(*settings.login_rate_limit_parsed)
    add_request_context_middleware(app)
    app.include_router(api_v1_router)  # prefixo /api/v1
    return app
```

- `lifespan`: cria `app.state.engine = create_async_engine(settings.database_url, pool_pre_ping=True)` e `app.state.sessionmaker = async_sessionmaker(engine, expire_on_commit=False)`; no shutdown, `await engine.dispose()`. Nada conecta no banco na importação nem em `create_app()` (o `export_openapi` depende disso).
- **Toda rota precisa de `tags=[...]`** (o `generate_unique_id_function` usa `route.tags[0]`); definir a tag no `APIRouter(tags=["auth"])`.
- `app/api/v1/router.py`: `api_v1_router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_origin)])`, incluindo `health.router` e `auth.router`.

**Resultado**: `uv run uvicorn app.main:create_app --factory --reload` sobe; `/api/docs` abre.

### 2.4 Banco: base, engine, health (T-05)

- `app/adapters/db/base.py`:
  - `NAMING_CONVENTION = {"ix": "ix_%(table_name)s_%(column_0_N_name)s", "uq": "uq_%(table_name)s_%(column_0_N_name)s", "ck": "ck_%(table_name)s_%(constraint_name)s", "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s", "pk": "pk_%(table_name)s"}`.
  - `class Base(DeclarativeBase): metadata = MetaData(naming_convention=NAMING_CONVENTION)`.
  - Mixins: `UUIDPrimaryKeyMixin` (`id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)`), `TimestampMixin` (`created_at`/`updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())`, `updated_at` com `onupdate=func.now()`).
- `app/adapters/db/engine.py`: `build_engine(settings) -> AsyncEngine` e `build_sessionmaker(engine)`.
- `app/core/container.py`: providers:
  - `get_settings_dep(request) -> Settings` (lê `request.app.state.settings`);
  - `async def get_db_session(request) -> AsyncIterator[AsyncSession]` (`async with request.app.state.sessionmaker() as session: yield session`);
  - `get_clock() -> Clock` (`SystemClock()`), `get_password_hasher() -> PasswordHasher` (instância única de `Argon2PasswordHasher`) — implementados na T-07.
- `app/api/deps.py`: aliases `DbSession = Annotated[AsyncSession, Depends(get_db_session)]`, `SettingsDep`, `ClockDep`, `HasherDep`.
- `app/api/v1/schemas/health.py`: `HealthResponse(status: Literal["ok", "degraded"], database: Literal["ok", "unavailable"])`.
- `app/api/v1/health.py`: `GET /health` (tag `health`, função `get_health` → operationId `health-get_health`): executa `SELECT 1` com timeout curto; sucesso → `200 {"status": "ok", "database": "ok"}`; exceção → `503` com `{"status": "degraded", "database": "unavailable"}` (usar `responses={503: {"model": HealthResponse}}` para aparecer no OpenAPI) e log de erro.

**Resultado**: com `just db-up`, `curl localhost:8000/api/v1/health` → `{"status":"ok","database":"ok"}`; com o banco parado → `503`.

### 2.5 Modelos e migração inicial (T-06)

- `app/adapters/db/models/user.py` — `class User(UUIDPrimaryKeyMixin, TimestampMixin, Base)`, `__tablename__ = "users"`: `email: Mapped[str] = mapped_column(String(320), unique=True)` (gera `uq_users_email`), `password_hash: Mapped[str] = mapped_column(Text)`.
- `app/adapters/db/models/session.py` — `class UserSession(UUIDPrimaryKeyMixin, Base)` (nome evita conflito com `Session` do SQLAlchemy), `__tablename__ = "sessions"`: `user_id` (FK `users.id`, `ondelete="CASCADE"`, indexado), `token_hash: Mapped[str] = mapped_column(String(64), unique=True)`, `created_at`, `last_seen_at`, `expires_at` (indexado), todos `timestamptz`.
- `app/adapters/db/models/__init__.py` importa `User` e `UserSession` (para o Alembic enxergar o metadata).
- Alembic: `cd backend && uv run alembic init migrations`, depois ajustar:
  - `alembic.ini`: remover `sqlalchemy.url`; `file_template = %%(rev)s_%%(slug)s`; `script_location = migrations`.
  - `migrations/env.py`: `target_metadata = Base.metadata`; URL = `config.get_main_option("sqlalchemy.url") or get_settings().database_url.render_as_string(hide_password=False)` (a opção permite que os testes apontem para o container); modo online **síncrono** com `create_engine(url)` (psycopg 3 serve para sync e async); `compare_type=True`.
- Gerar: `uv run alembic revision --autogenerate --rev-id 0001 -m "initial"` → `migrations/versions/0001_initial.py`. **Revisar à mão**: nomes de constraints, `ondelete="CASCADE"`, índices de `user_id` e `expires_at`, `server_default=now()`; `downgrade()` remove `sessions` e depois `users`.
- Receitas `just migrate` (`cd backend && uv run alembic upgrade head`) e `just migration "msg"` (`cd backend && uv run alembic revision --autogenerate -m "{{msg}}"`).

**Resultado**: `just migrate` cria `users` e `sessions`; `uv run alembic downgrade base` remove as duas sem erro.

### 2.6 Ports, adapters e fakes (T-07)

| Arquivo | Conteúdo |
|---|---|
| `app/ports/clock.py` | `class Clock(Protocol): def now(self) -> datetime: ...` (sempre timezone-aware, UTC) |
| `app/ports/password_hasher.py` | `class PasswordHasher(Protocol)`: `hash(password: str) -> str`, `verify(password_hash: str, password: str) -> bool`, `needs_rehash(password_hash: str) -> bool` |
| `app/adapters/clock.py` | `SystemClock.now()` → `datetime.now(UTC)` |
| `app/adapters/security/argon2_hasher.py` | `Argon2PasswordHasher` sobre `argon2.PasswordHasher()` (parâmetros padrão, Argon2id); `verify` captura `VerifyMismatchError`/`InvalidHashError` e retorna `False` |
| `tests/fakes/clock.py` | `FakeClock(start: datetime)` com `now()` e `advance(delta: timedelta)` |
| `tests/fakes/password_hasher.py` | `FakePasswordHasher`: `hash(p) = "fake$" + p`; `verify` compara; `needs_rehash` → `False` |

Completar `core/container.py` com `get_clock` e `get_password_hasher`.

### 2.7 Domínio puro (T-08)

`app/domain/auth.py` (sem I/O, sem SQLAlchemy, sem FastAPI):

```python
SESSION_RENEW_INTERVAL = timedelta(hours=1)

def normalize_email(email: str) -> str            # strip + lower
def hash_session_token(token: str) -> str         # sha256(token).hexdigest()
def session_expires_at(now: datetime, ttl: timedelta) -> datetime
def is_session_expired(expires_at: datetime, now: datetime) -> bool   # expires_at <= now
def should_renew_session(last_seen_at: datetime, now: datetime) -> bool  # now - last_seen_at > 1h
```

Funções puras e pequenas; a geração do token (`secrets.token_urlsafe(32)`) fica na `application/` porque é aleatória.

### 2.8 Casos de uso (T-09)

`app/application/auth/` — todos `async`, recebem `AsyncSession` e ports como argumentos (nada de import de adapter):

| Módulo | Assinatura | Comportamento |
|---|---|---|
| `errors.py` | `InvalidCredentials`, `UserAlreadyExists` | Exceções da aplicação |
| `dto.py` | `@dataclass(frozen=True) AuthenticatedUser(id: UUID, email: str)`; `LoginResult(token: str, expires_at: datetime)` | DTOs devolvidos à API |
| `login.py` | `login(db, hasher, clock, *, email, password, ttl) -> LoginResult` | Busca usuário por `normalize_email(email)`. Se não existir, executa `hasher.verify(DUMMY_HASH, password)` para igualar o tempo e lança `InvalidCredentials`. Se a senha não confere, `InvalidCredentials`. Se `hasher.needs_rehash`, atualiza o hash. Gera token, grava `UserSession(token_hash=hash_session_token(token), created_at=now, last_seen_at=now, expires_at=session_expires_at(now, ttl))`, `commit`. |
| `resolve_session.py` | `resolve_session(db, clock, *, token, ttl) -> AuthenticatedUser \| None` | Busca a sessão por `token_hash` com join no usuário. Ausente → `None`. Expirada → apaga, `commit`, `None`. Se `should_renew_session`, atualiza `last_seen_at` e `expires_at`, `commit`. Retorna o DTO. |
| `logout.py` | `logout(db, *, token) -> None` | Apaga a sessão pelo `token_hash` (idempotente), `commit`. |
| `create_user.py` | `create_user(db, hasher, *, email, password) -> AuthenticatedUser` | Normaliza o e-mail; valida formato mínimo (contém um `@` com texto dos dois lados) e senha com **pelo menos 12 caracteres**; `UserAlreadyExists` se o e-mail já existir; grava com `hasher.hash(password)`, `commit`. |

`DUMMY_HASH`: gerado uma vez por processo com `hasher.hash("dummy-password")` (cache em atributo de módulo) — assim o tempo de resposta não revela se o e-mail existe.

### 2.9 Camada HTTP de auth (T-10)

**`app/core/rate_limit.py`** — `InMemoryRateLimiter(limit: int, window_seconds: int)`: `dict[str, deque[float]]` com timestamps `time.monotonic()`; `hit(key) -> bool` descarta entradas fora da janela, retorna `False` se já houver `limit` entradas, senão registra e retorna `True`. Instância por app (`app.state.login_rate_limiter`), então cada app de teste começa zerada.

**`app/api/deps.py`** (além dos aliases da 2.4):
- `verify_origin(request, settings)`: se o método é `POST/PUT/PATCH/DELETE`, exige header `Origin` presente e em `settings.allowed_origins`; senão `HTTPException(403, "Invalid origin")`. Aplicado no router da v1 (2.3).
- `login_rate_limit(request)`: chave = `request.client.host` (o IP real chega via `--proxy-headers`); excedido → `HTTPException(429, "Too many login attempts")`.
- `current_user(request, db, clock, settings) -> AuthenticatedUser`: lê o cookie `settings.session_cookie_name`; ausente ou `resolve_session` → `None` ⇒ `HTTPException(401, "Not authenticated")`. Alias `CurrentUser = Annotated[AuthenticatedUser, Depends(current_user)]`.

**`app/api/v1/schemas/auth.py`**: `LoginRequest(email: str = Field(max_length=320), password: str = Field(min_length=1, max_length=1024))` (sem `EmailStr`: o login responde de forma genérica de qualquer jeito, e evita a dependência `email-validator`); `MeResponse(id: UUID, email: str)`.

**`app/api/v1/auth.py`** (`APIRouter(prefix="/auth", tags=["auth"])`):

| Rota | Função (operationId) | Detalhes |
|---|---|---|
| `POST /login` | `login` (`auth-login`) | `dependencies=[Depends(login_rate_limit)]`, `status_code=204`. `InvalidCredentials` → `401 "Invalid email or password"` (mesma resposta para usuário inexistente e senha errada). Sucesso: `response.set_cookie(key=cookie_name, value=token, max_age=ttl_days*86400, httponly=True, secure=settings.session_cookie_secure, samesite="lax", path="/")`. |
| `POST /logout` | `logout` (`auth-logout`) | `204`. Se houver cookie, chama `logout`; sempre `response.delete_cookie(cookie_name, path="/")`. Não exige sessão válida. |
| `GET /me` | `me` (`auth-me`) | `response_model=MeResponse`; recebe `CurrentUser`; `401` se não autenticado. |

Para devolver `204` com cookie, declarar `response: Response` no parâmetro e `status_code=204` no decorator (retornando `None`), ou retornar `Response(status_code=204)` após `set_cookie` nele.

**Resultado**: fluxo completo via `/api/docs` (com header `Origin` — por `curl`, usar `-H "Origin: http://localhost:8000"`).

### 2.10 CLI, seed e exportação do OpenAPI (T-11, T-12)

**`app/cli/__main__.py`** — `argparse` com subcomandos; cada um roda `asyncio.run(...)` com engine/sessionmaker criados a partir do `Settings` (reaproveita os casos de uso async; psycopg 3 atende os dois modos):
- `create-user <email>`: senha via `getpass.getpass()` duas vezes (confirmação), nunca por argumento; `create_user` com `Argon2PasswordHasher`; mensagens em pt-BR; código de saída `1` em `UserAlreadyExists` ou validação.
- `seed-dev`: ver seção 3.

**`app/scripts/export_openapi.py`**: `print(json.dumps(create_app().openapi(), indent=2, ensure_ascii=False))`. Não conecta no banco (o lifespan não roda).

Receitas: `just create-user email` (`cd backend && uv run python -m app.cli create-user {{email}}`), `just seed`, `just gen-client` (2.12).

### 2.11 Frontend: projeto e ferramentas (T-15)

**Onde**: `frontend/`.

1. `pnpm create vite@latest frontend --template react-ts` (a partir da raiz) e limpar o boilerplate (`App.tsx`, `App.css`, assets de exemplo).
2. `frontend/.nvmrc`: `26`; `package.json`: `"packageManager": "pnpm@<versão instalada>"`, `"engines": { "node": ">=26" }`, scripts `dev`, `build` (`tsc -b && vite build`), `preview`, `test` (`vitest run`), `lint` (`eslint .`), `typecheck` (`tsc -b --noEmit` ou `tsc --noEmit -p tsconfig.app.json`, conforme o template), `format` (`prettier --write .`), `format:check`.
3. Dependências (versões atuais, conferindo a documentação): runtime `react`, `react-dom`, `@tanstack/react-router`, `@tanstack/react-query`, `openapi-fetch`, `openapi-react-query`, `tailwindcss`, `@tailwindcss/vite`; dev `@tanstack/router-plugin`, `vite-plugin-pwa`, `openapi-typescript`, `vitest`, `jsdom`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `msw`, `openapi-msw`, `eslint`, `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `eslint-config-prettier`, `prettier`, `prettier-plugin-tailwindcss`.
4. `tsconfig`: `strict: true`, `noUncheckedIndexedAccess: true`, alias `@/*` → `src/*` (exigido pelo shadcn); `types` incluindo `vite-plugin-pwa/react` e `vitest/globals` se usar globals.
5. `vite.config.ts`: plugins na ordem `tanstackRouter({ target: "react", autoCodeSplitting: true })` (**antes** de `react()`), `react()`, `tailwindcss()`, `VitePWA({...})` (2.14); `resolve.alias` `@` → `src`; `server: { port: 5173, proxy: { "/api": "http://localhost:8000" } }`; bloco `test` (2.15).
6. Tailwind v4: `src/index.css` com `@import "tailwindcss";` + tokens do tema.
7. shadcn/ui: `pnpm dlx shadcn@latest init` (gera `components.json`, `src/lib/utils.ts` com `cn()`); adicionar `button`, `input`, `label`, `card`, `sonner`.
8. ESLint flat (`eslint.config.js`): `typescript-eslint` type-checked, `react-hooks`, `react-refresh`, `eslint-config-prettier`; ignorar `dist`, `dev-dist`, `src/routeTree.gen.ts`, `src/api/schema.d.ts`, `src/components/ui/**` (gerado pelo shadcn; opcional).
9. Prettier: `.prettierrc` (`{ "plugins": ["prettier-plugin-tailwindcss"] }`) e **`.prettierignore`** com `src/routeTree.gen.ts`, `src/api/schema.d.ts`, `dist`, `dev-dist`, `pnpm-lock.yaml`.

### 2.12 Client da API (T-16)

- Receita `just gen-client`:

```just
gen-client:
    tmp="$(mktemp --suffix .json)"; \
    (cd backend && uv run python -m app.scripts.export_openapi) > "$tmp"; \
    pnpm --dir frontend exec openapi-typescript "$tmp" -o src/api/schema.d.ts; \
    rm -f "$tmp"
```

  Só `frontend/src/api/schema.d.ts` é versionado.
- `src/api/client.ts`:

```ts
import createFetchClient from "openapi-fetch";
import createClient from "openapi-react-query";
import type { paths } from "./schema";

export const fetchClient = createFetchClient<paths>({
  baseUrl: window.location.origin, // mesma origem; absoluto para funcionar também no jsdom
  credentials: "same-origin",
});
export const $api = createClient(fetchClient);
export const meQueryOptions = () => $api.queryOptions("get", "/api/v1/auth/me");
```

- Middleware do `fetchClient` (`fetchClient.use({ onResponse })`): em `401` de qualquer rota **exceto** `/api/v1/auth/me` e `/api/v1/auth/login`, remover a query `me` do cache e navegar para `/login?redirect=<path atual>` usando o `router` exportado de `src/router.ts`.
- `src/api/query-client.ts`: `new QueryClient({ defaultOptions: { queries: { retry: (count, err) => count < 2 && !isUnauthorized(err), staleTime: 30_000 } } })`.

### 2.13 Rotas, telas e features (T-17, T-18)

- `src/router.ts`: `createRouter({ routeTree, context: { queryClient }, defaultPreload: "intent" })` + `declare module "@tanstack/react-router" { interface Register { router: typeof router } }`.
- `src/main.tsx`: `QueryClientProvider` + `RouterProvider`; importa `index.css`.
- `src/routes/__root.tsx`: `createRootRouteWithContext<{ queryClient: QueryClient }>()`; renderiza `<Outlet />`, `<Toaster />` (sonner) e `<PwaUpdatePrompt />`.
- `src/routes/login.tsx`: `validateSearch` aceitando `redirect?: string` (só caminhos que começam com `/` e não com `//`, para evitar open redirect); renderiza `LoginForm` com `onLoggedIn={() => navigate({ to: redirect ?? "/" })}`. Se já autenticado (`me` no cache), redireciona para `/`.
- `src/routes/_authenticated.tsx`: `beforeLoad: async ({ context, location }) => { try { await context.queryClient.ensureQueryData(meQueryOptions()) } catch { throw redirect({ to: "/login", search: { redirect: location.href } }) } }`; componente `AppShell` com `<Outlet />`.
- `src/routes/_authenticated/index.tsx`: título "Início" e `<HealthStatus />`.
- `src/features/auth/useLogin.ts`: `$api.useMutation("post", "/api/v1/auth/login", { onSuccess: () => queryClient.invalidateQueries({ queryKey: meQueryOptions().queryKey }) })`.
- `src/features/auth/useLogout.ts`: mutation `post /api/v1/auth/logout`; `onSettled`: `queryClient.clear()` e navegar para `/login`.
- `src/features/auth/LoginForm.tsx`: e-mail e senha (`Input`, `Label`, `Button` do shadcn), botão "Entrar" com estado "Entrando…"; erro `401` → "E-mail ou senha inválidos."; `429` → "Muitas tentativas. Aguarde um minuto e tente de novo."; outros → "Não foi possível entrar. Tente novamente."; prop `onLoggedIn: () => void` (o componente **não** navega, o que o mantém testável sem router).
- `src/features/health/HealthStatus.tsx`: `$api.useQuery("get", "/api/v1/health")` direto (sem hook próprio); estados "Verificando…", "API: ok · Banco: ok" e "Backend indisponível" (erro ou `503`).
- `src/components/layout/AppShell.tsx`: cabeçalho "Vocabulary Builder", e-mail do usuário (`useQuery(meQueryOptions())`) e botão "Sair" (`useLogout`); layout mobile-first.

**Resultado**: em `http://localhost:5173`, `/` redireciona para `/login`; após login com o usuário do seed, mostra o status; "Sair" volta ao login.

### 2.14 PWA (T-19)

- Ícones: `pnpm dlx @vite-pwa/assets-generator --preset minimal-2023 public/favicon.svg` a partir de um `favicon.svg` simples. Gera `pwa-64x64.png`, `pwa-192x192.png`, `pwa-512x512.png`, `maskable-icon-512x512.png` e `apple-touch-icon-180x180.png` em `public/` (essa nomenclatura substitui a pasta `public/icons/` citada na spec).
- `VitePWA({ registerType: "prompt", manifest: { name: "Vocabulary Builder", short_name: "Vocab", lang: "pt-BR", display: "standalone", start_url: "/", theme_color, background_color, icons: [192, 512, 512 maskable] }, workbox: { globPatterns: ["**/*.{js,css,html,svg,png,webmanifest}"], navigateFallbackDenylist: [/^\/api\//] } })`. **Nenhum `runtimeCaching` para `/api/*`.**
- `index.html`: `<link rel="apple-touch-icon" href="/apple-touch-icon-180x180.png">`, `<meta name="theme-color">`, `lang="pt-BR"`.
- `src/components/PwaUpdatePrompt.tsx`: `useRegisterSW()` de `virtual:pwa-register/react`; quando `needRefresh`, toast "Nova versão disponível" com ação "Atualizar" → `updateServiceWorker(true)`.

**Resultado**: `pnpm build && pnpm preview` gera `sw.js` e `manifest.webmanifest`; Lighthouse/DevTools reconhece como instalável.

### 2.15 Imagens, compose de produção e deploy (T-23 a T-30)

**`backend/Dockerfile`** (imagem `api`):

```dockerfile
FROM python:3.14-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:<versão fixa> /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini ./

FROM python:3.14-slim
LABEL org.opencontainers.image.source="https://github.com/sgabriel-santos/vocabulary-builder"
RUN useradd --uid 1000 --create-home app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4)"]
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
```

- `--forwarded-allow-ips "*"` é aceitável porque a `api` não publica portas e só o Caddy a alcança pela rede interna; se possível, restringir à sub-rede da rede do Compose.
- `backend/.dockerignore`: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `tests/`, `.env*`, `htmlcov/`, `.coverage`.

**`frontend/Dockerfile`** (imagem `web`):

```dockerfile
FROM node:26-slim AS build
RUN npm install -g pnpm@<versão do packageManager>
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM caddy:2.<x>-alpine
LABEL org.opencontainers.image.source="https://github.com/sgabriel-santos/vocabulary-builder"
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80 443 443/udp
```

- `frontend/.dockerignore`: `node_modules/`, `dist/`, `dev-dist/`, `coverage/`, `.env*`, `e2e/`.
- O Caddy oficial roda como root; manter assim na E0 (rodar não-root exige validar `cap_net_bind_service` — avaliar depois).

**`frontend/Caddyfile`**:

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
    @sw path /sw.js /index.html /manifest.webmanifest
    header @sw Cache-Control "no-cache"
}
```

**`deploy/compose.prod.yaml`**:

| Serviço | Configuração |
|---|---|
| `db` | `postgres:18.<minor>-alpine`; `environment: POSTGRES_DB: ${POSTGRES_DB}, POSTGRES_USER: ${POSTGRES_USER}, POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password`; `secrets: [postgres_password]`; volume `db_data:/var/lib/postgresql`; healthcheck `pg_isready`; sem `ports`; limites 1 CPU / 1 GB. |
| `migrate` | `ghcr.io/sgabriel-santos/vocab-api:${IMAGE_TAG}`; `command: ["alembic", "upgrade", "head"]`; `env_file: ../.env`; `secrets: [postgres_password]`; `depends_on: { db: { condition: service_healthy } }`; `restart: "no"`; limites 0.5 CPU / 512 MB. |
| `api` | mesma imagem; `env_file: ../.env`; `secrets: [postgres_password]`; `depends_on: { db: service_healthy, migrate: service_completed_successfully }`; sem `ports`; limites 1 CPU / 1 GB. |
| `web` | `ghcr.io/sgabriel-santos/vocab-web:${IMAGE_TAG}`; `ports: ["80:80", "443:443", "443:443/udp"]`; `environment: APP_DOMAIN: ${APP_DOMAIN}`; volumes `caddy_data:/data` e `caddy_config:/config` (**obrigatórios**: guardam os certificados; perdê-los esbarra no rate limit do Let's Encrypt); `depends_on: [api]`; limites 0.5 CPU / 256 MB. |

Comum: `restart: unless-stopped` (exceto `migrate`); `logging: { driver: json-file, options: { max-size: "10m", max-file: "3" } }`; uma rede interna; **nunca** montar `/var/run/docker.sock`. `secrets: { postgres_password: { file: ./secrets/postgres_password } }`; volumes `db_data`, `caddy_data`, `caddy_config`.

O `.env` de produção (`/opt/vocab/.env`, `chmod 600`) contém: `APP_ENV=production`, `APP_DOMAIN=vocab.<domínio>`, `LOG_LEVEL=INFO`, `LOG_FORMAT=json`, `POSTGRES_HOST=db`, `POSTGRES_PORT=5432`, `POSTGRES_DB=vocab`, `POSTGRES_USER=vocab`, `SESSION_COOKIE_SECURE=true`, `SESSION_TTL_DAYS=60`, `LOGIN_RATE_LIMIT=5/minute`. **Sem `POSTGRES_PASSWORD`** (variável de ambiente tem precedência sobre `/run/secrets` no pydantic-settings).

**`deploy/deploy.sh <sha> <ghcr_user>`** (executável, `set -euo pipefail`):
1. Valida `<sha>` com `^[0-9a-f]{40}$`.
2. `cd /opt/vocab/deploy`; lê o token do stdin (`read -r token`) e faz `docker login ghcr.io -u "$2" --password-stdin <<< "$token"`.
3. `export IMAGE_TAG="$1"`; `docker compose --env-file /opt/vocab/.env -f compose.prod.yaml pull`.
4. `docker compose --env-file /opt/vocab/.env -f compose.prod.yaml up -d --remove-orphans` (o `migrate` roda antes da `api` pelo `depends_on`).
5. Smoke test: até 10 tentativas, 6 s de intervalo, `curl -fsS "https://$APP_DOMAIN/api/v1/health"` (ler `APP_DOMAIN` do `.env`).
6. Sucesso: `echo "$1" > /opt/vocab/current_tag`; remover imagens antigas mantendo as duas tags mais recentes de cada repositório; `docker logout ghcr.io`.
7. Falha: `docker logout ghcr.io`, mensagem clara, `exit 1` (sem gravar `current_tag`).

**`deploy/README.md`** (runbook): setup do VPS (T-26), layout de `/opt/vocab`, criação do usuário em produção (`docker compose --env-file /opt/vocab/.env -f compose.prod.yaml run --rm api python -m app.cli create-user <email>`), rollback manual e, como pendência, a seção de backup/restore que entra na E1.

**Workflows** — ver T-22 e T-28 na seção 5.

---

## 3. Plano de seed

### 3.1 O que gerar

**Um usuário de desenvolvimento** (`users`), com as credenciais de `SEED_USER_EMAIL` / `SEED_USER_PASSWORD` (padrão `dev@example.com` / `dev-password-123`; `example.com` é domínio reservado, sem risco de ser um e-mail real). Na E0 não há outra entidade; sessões nascem do login. A partir da E1, o mesmo comando passa a criar termos de exemplo (o `seed-dev` é o ponto de extensão).

### 3.2 Onde fica

- Lógica: `backend/app/cli/__main__.py`, subcomando `seed-dev`, reutilizando o caso de uso `create_user` (2.8).
- Configuração: campos `seed_user_email` e `seed_user_password` do `Settings` e as variáveis correspondentes no `.env.example`.

### 3.3 Comportamento

1. Se `settings.app_env == "production"`: imprime "seed-dev não pode rodar em produção" e sai com código `1`.
2. Se o usuário já existe: imprime "Usuário de desenvolvimento já existe: <email>" e sai com `0` (**idempotente**).
3. Senão: cria o usuário e imprime "Usuário de desenvolvimento criado: <email>" (nunca imprime a senha).

### 3.4 Como executar

```bash
just db-up
just migrate
just seed          # cd backend && uv run python -m app.cli seed-dev
```

Após `docker compose down -v` (banco zerado), basta repetir `just migrate && just seed`.

### 3.5 Variações representativas

Na E0 a variação de dados está nos **testes de API**, não no seed: usuário inexistente, senha errada, sessão expirada (via `FakeClock`), sessão perto da renovação, e-mail com maiúsculas/espaços (normalização). O seed serve apenas para o login manual no navegador.

> **Desvio da spec**: a spec não prevê seed. Esta adição (`just seed`, subcomando `seed-dev`, duas variáveis no `.env.example`) foi aprovada no planejamento e já está registrada nas seções 5.2, 5.3 e 13 da spec.

---

## 4. Plano de testes

Regras: nenhum teste chama serviço externo; lógica temporal usa `Clock`; testes de integração e API usam Postgres real via testcontainers (Docker precisa estar rodando).

### 4.1 Setup do backend (T-13)

**`tests/conftest.py`** (fixtures compartilhadas; as de banco só iniciam o container quando algum teste as pede, então `pytest -m unit` continua sem Docker):

- `test_settings` → `Settings(app_env="test", session_cookie_secure=False, login_rate_limit="5/minute")`.
- `fake_clock` → `FakeClock(datetime(2026, 1, 1, 12, tzinfo=UTC))`.
- `postgres_url` (escopo `session`): `PostgresContainer("postgres:18.<minor>-alpine", driver="psycopg")` → `get_connection_url()`; roda `alembic upgrade head` via `alembic.command.upgrade(cfg, "head")`, com `cfg = Config("alembic.ini")` e `cfg.set_main_option("sqlalchemy.url", url)`.
- `engine` (escopo `session`, async): `create_async_engine(postgres_url)`; `dispose()` ao final.
- `db_session` (por teste): `async with engine.connect() as conn: trans = await conn.begin()`; `AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)`; `yield`; fecha a sessão e `await trans.rollback()`. Os `commit()` dos casos de uso viram savepoints e tudo é desfeito no fim.

> A spec coloca o container em `tests/integration/conftest.py`; aqui ele fica no `tests/conftest.py` para que `integration/` e `api/` compartilhem **um** container por sessão. Os `conftest.py` de `integration/` e `api/` ficam com o que é específico de cada pasta.

**`tests/api/conftest.py`**:
- `app` → `create_app(test_settings)` com `dependency_overrides`: `get_db_session` → `db_session`; `get_password_hasher` → `FakePasswordHasher()`; `get_clock` → `fake_clock`.
- `client` → `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost:8000", headers={"Origin": "http://localhost:8000"})`. O `ASGITransport` não roda o lifespan; por isso a sessão de DB vem do override.
- `user` → insere `User(email="user@example.com", password_hash="fake$correct-password-123")` via `db_session` e `flush()`.

Marcadores: cada arquivo declara `pytestmark = pytest.mark.unit` (ou `integration`/`api`), ou aplicar automaticamente por pasta num hook `pytest_collection_modifyitems` no `tests/conftest.py` (preferível: evita esquecer o marker).

### 4.2 Testes unitários (`tests/unit/`)

`test_auth_domain.py`:
- `test_normalize_email_lowercases_and_strips`
- `test_session_is_expired_at_exact_expiry` e `test_session_not_expired_before_expiry`
- `test_session_renewed_only_after_one_hour` (com `FakeClock.advance`)
- `test_hash_session_token_is_deterministic_and_not_plaintext`

`test_rate_limit.py`: `test_rate_limiter_blocks_after_limit` e `test_rate_limiter_releases_after_window` (injetar uma função de tempo no limiter, com default `time.monotonic`, para não usar `sleep`).

### 4.3 Testes de integração (`tests/integration/`)

`test_migrations.py`:
- `test_migrations_downgrade_to_base_and_upgrade_to_head`: `downgrade base` e depois `upgrade head` contra o container, sem erro (termina em `head` para não afetar os outros testes).
- `test_users_email_is_unique`: dois `User` com o mesmo e-mail → `IntegrityError` com `uq_users_email`.
- `test_deleting_user_cascades_sessions`.

### 4.4 Testes de API (`tests/api/`)

`test_health.py`: `test_health_returns_ok`.

`test_auth.py`:
- `test_login_sets_http_only_cookie_and_me_returns_user` (checar `HttpOnly`, `SameSite=lax`, `Path=/`)
- `test_login_with_wrong_password_returns_generic_401`
- `test_login_with_unknown_email_returns_same_401` (mesmo status e corpo do caso anterior)
- `test_login_normalizes_email` (`" User@Example.com "`)
- `test_me_without_cookie_returns_401`
- `test_logout_invalidates_session` (após logout, `/me` → `401`, mesmo reenviando o cookie antigo)
- `test_expired_session_returns_401` (`fake_clock.advance(days=61)`)
- `test_post_without_origin_returns_403` e `test_post_with_foreign_origin_returns_403`
- `test_login_rate_limit_returns_429_after_five_attempts`

### 4.5 Testes de frontend (T-20)

- `vite.config.ts`, bloco `test`: `environment: "jsdom"`, `environmentOptions: { jsdom: { url: "http://localhost:5173" } }` (fixa o `window.location.origin` usado pelo client), `setupFiles: ["./src/test/setup.ts"]`, `globals: true`.
- `src/test/handlers.ts`: `const http = createOpenApiHttp<paths>({ baseUrl: "http://localhost:5173" })`; handlers padrão para `get /api/v1/health` (ok) e `get /api/v1/auth/me` (401).
- `src/test/setup.ts`: `import "@testing-library/jest-dom/vitest"`; `setupServer(...handlers)`; `beforeAll(listen({ onUnhandledRequest: "error" }))`, `afterEach(resetHandlers)`, `afterAll(close)`.
- `src/test/render.tsx`: helper que envolve o componente em `QueryClientProvider` com `retry: false`.
- `src/features/auth/LoginForm.test.tsx`: envio bem-sucedido chama `onLoggedIn`; `401` mostra "E-mail ou senha inválidos."; `429` mostra a mensagem de limite.
- `src/features/health/HealthStatus.test.tsx`: sucesso mostra "API: ok · Banco: ok"; `503` mostra "Backend indisponível".
- **E2E de frontend (Playwright): fora da E0**, entra na E1 com o primeiro fluxo real. Na E0, o fluxo no navegador é validado manualmente (critério de sucesso 1 e 4).

### 4.6 Como executar (receitas do `justfile`)

| Receita | Executa |
|---|---|
| `just setup` | `.env` a partir do exemplo, `uv sync`, `pnpm install`, hooks de pre-commit |
| `just db-up` / `just db-down` | Postgres do `compose.yaml` |
| `just dev` | `db-up` + `dev-backend` + `dev-frontend` em paralelo (`trap 'kill 0' EXIT; just dev-backend & just dev-frontend & wait`) |
| `just dev-backend` | `cd backend && uv run uvicorn app.main:create_app --factory --reload --port 8000` |
| `just dev-frontend` | `pnpm --dir frontend dev` |
| `just migrate` / `just migration "msg"` | Alembic |
| `just create-user <email>` / `just seed` | CLI |
| `just lint` | `lint-backend` (`ruff check` + `ruff format --check`) + `lint-frontend` (`eslint` + `prettier --check`) |
| `just format` | `ruff format` + `ruff check --fix` + `prettier --write` |
| `just typecheck` | `typecheck-backend` (`mypy`) + `typecheck-frontend` (`tsc`) |
| `just test` | `test-backend` + `test-frontend` |
| `just test-unit` / `test-integration` / `test-api` | `cd backend && uv run pytest -m <marker>` |
| `just test-backend` | `cd backend && uv run pytest --cov --cov-report=xml --cov-report=term` |
| `just test-frontend` | `pnpm --dir frontend test` |
| `just build-frontend` | `pnpm --dir frontend build` |
| `just gen-client` | 2.12 |
| `just build` | `build-frontend` + `docker build` das imagens `api` e `web` localmente |
| `just deploy-rollback <sha>` | `gh workflow run deploy.yml -f sha={{sha}}` |

---

## 5. Sequência de implementação

Branches: o PR atual (`docs/e0-scaffolding-spec`) é mergeado primeiro. A implementação acontece em `chore/e0-walking-skeleton`. Um PR único é aceitável na E0, mas **o merge na `main` só acontece depois da T-27** (o merge dispara o deploy). Cada tarefa termina em um commit proposto ao usuário (aprovação explícita antes de cada um).

**Fase A — Ambiente e base**

1. **T-01 (manual, você)** — Instalar Node 26 (`nvm install 26 && nvm alias default 26`), pnpm standalone (`curl -fsSL https://get.pnpm.io/install.sh | sh -`), `just` (`uv tool install rust-just`) e, opcionalmente, `gh` (`gh auth login`). Conferir `node -v`, `pnpm -v`, `just --version`.
2. **T-02** — Arquivos da raiz, `.env.example`, `compose.yaml`, `justfile` inicial (2.1). Verificar: `just db-up` → Postgres saudável.

**Fase B — Backend (login local por API)**

3. **T-03** — Projeto Python e configs de ferramentas (2.2).
4. **T-04** — `config`, `logging`, `middleware`, `main.py`, router da v1 (2.3).
5. **T-05** — Base ORM, engine, container, `GET /api/v1/health` (2.4).
6. **T-06** — Modelos `User`/`UserSession`, Alembic, migração `0001_initial` revisada (2.5).
7. **T-07** — Ports `Clock`/`PasswordHasher`, adapters e fakes (2.6).
8. **T-08** — `domain/auth.py` + testes unitários (2.7, 4.2).
9. **T-09** — Casos de uso de `application/auth/` (2.8).
10. **T-10** — Rate limiter, `verify_origin`, `current_user`, schemas e router de auth (2.9).
11. **T-11** — CLI `create-user` e `seed-dev`; receitas `create-user` e `seed` (2.10, 3).
12. **T-12** — `export_openapi.py` (2.10).
13. **T-13** — Fixtures de teste do backend (4.1).
14. **T-14** — Testes de integração e de API (4.3, 4.4). Verificar: `just lint-backend`, `just typecheck-backend`, `just test-backend` verdes.

**Fase C — Frontend (login local no navegador)**

15. **T-15** — Projeto Vite, TS strict, ESLint, Prettier, Tailwind, shadcn (2.11).
16. **T-16** — `just gen-client`, `schema.d.ts`, `client.ts`, `query-client.ts` (2.12).
17. **T-17** — Router, `main.tsx`, rotas `__root`, `login`, `_authenticated`, `_authenticated/index` (2.13).
18. **T-18** — `LoginForm`, `useLogin`, `useLogout`, `HealthStatus`, `AppShell` (2.13). **Marco: critério de sucesso 1** (login local de ponta a ponta com `just dev` + `just seed`).
19. **T-19** — PWA: ícones, manifest, service worker, prompt de atualização (2.14).
20. **T-20** — Testes de frontend (4.5). Verificar: `just lint`, `just typecheck`, `just test` verdes.

**Fase D — Qualidade e CI**

21. **T-21** — `.pre-commit-config.yaml`: `pre-commit-hooks` (`trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-merge-conflict`, `check-added-large-files`, `mixed-line-ending --fix=lf`), `ruff-pre-commit` (`ruff-check --fix`, `ruff-format`) em `backend/`, hook local de ESLint + Prettier nos arquivos staged de `frontend/` (`pnpm --dir frontend exec ...`, com caminhos relativos ajustados), `gitleaks`. Sem hook `commit-msg`. Atualizar `just setup`. Rodar `uvx pre-commit run --all-files`.
22. **T-22** — `.github/workflows/ci.yml` com gatilhos `pull_request`, `push` (`branches-ignore: [main]`) e `workflow_call`; `permissions: contents: read`; jobs `backend`, `frontend`, `contract`, `secrets` conforme abaixo. Fazer push da branch e confirmar CI verde.

| Job | Passos |
|---|---|
| `backend` | checkout → `astral-sh/setup-uv` (versão fixa, `enable-cache`) → `extractions/setup-just` → `uv sync --frozen` (em `backend/`) → `just lint-backend` → `just typecheck-backend` → `just test-backend` → upload de `coverage.xml` como artefato |
| `frontend` | checkout → `pnpm/action-setup` → `actions/setup-node` (`node-version-file: frontend/.nvmrc`, `cache: pnpm`, `cache-dependency-path: frontend/pnpm-lock.yaml`) → `pnpm install --frozen-lockfile` → `just lint-frontend` → `just typecheck-frontend` → `just test-frontend` → `just build-frontend` |
| `contract` | setup uv + pnpm + just → `uv sync --frozen` → `pnpm install --frozen-lockfile` → `just gen-client` → `git diff --exit-code frontend/src/api/` |
| `secrets` | checkout com `fetch-depth: 0` → gitleaks (action oficial ou binário fixado) |

**Fase E — Produção**

23. **T-23** — `backend/Dockerfile` e `.dockerignore` (2.15). Verificar: `docker build` local e `docker run` contra o Postgres de dev (`--network host`, `POSTGRES_HOST=localhost`) responde em `/api/v1/health`.
24. **T-24** — `frontend/Dockerfile`, `.dockerignore`, `Caddyfile` (2.15). Verificar: `docker build` local conclui.
25. **T-25** — `deploy/compose.prod.yaml`, `deploy/deploy.sh` (executável), `deploy/secrets/.gitkeep`, `deploy/README.md` (2.15). Verificar: `docker compose -f deploy/compose.prod.yaml config` válido (com variáveis fictícias).
26. **T-26 (manual, você, seguindo o runbook)** — Configurar o VPS:
    1. Usuário administrativo com sudo; `PasswordAuthentication no`, `PermitRootLogin no`.
    2. Firewall (`ufw` ou do provedor): 22, 80, 443/tcp, 443/udp; `unattended-upgrades`.
    3. Docker Engine + plugin Compose (repositório oficial).
    4. Usuário `deploy` (grupo `docker`, sem sudo), dono de `/opt/vocab`; gerar um par de chaves **exclusivo do deploy** (`ssh-keygen -t ed25519 -C vocab-deploy`) e colocar a pública em `~deploy/.ssh/authorized_keys` com `no-port-forwarding,no-agent-forwarding,no-X11-forwarding` (sem `command=`). Garantir que `rsync` esteja instalado.
    5. `/opt/vocab/.env` (conteúdo em 2.15, `chmod 600`) e `/opt/vocab/deploy/secrets/postgres_password` (senha forte, `chmod 600`, dono `deploy`).
    6. DNS no Registro.br: registro `A` `vocab` → IP do VPS (e `AAAA` se houver IPv6). Conferir com `dig vocab.<domínio>`.
27. **T-27 (manual, você)** — GitHub: Environment `production` com *deployment branch rule* só para `main`; secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS` (saída de `ssh-keyscan -t ed25519 <host>` conferida contra a fingerprint vista no console do VPS); variável `APP_DOMAIN`.
28. **T-28** — `.github/workflows/deploy.yml` e `.github/dependabot.yml`:
    - Gatilhos: `push` em `main`; `workflow_dispatch` com input `sha` (obrigatório). `concurrency: { group: production, cancel-in-progress: false }`.
    - Job `ci`: `uses: ./.github/workflows/ci.yml`; `if: github.event_name == 'push'`.
    - Job `build-and-push` (`needs: ci`, `if: push`, `permissions: contents: read, packages: write`): `docker/setup-buildx-action` → `docker/login-action` (GHCR, `GITHUB_TOKEN`) → `docker/build-push-action` duas vezes (`context: backend` → `ghcr.io/sgabriel-santos/vocab-api:${{ github.sha }}`; `context: frontend` → `.../vocab-web:${{ github.sha }}`), `platforms: linux/amd64`, `cache-from/to: type=gha` (com `scope` distinto por imagem).
    - Job `deploy` (`needs: build-and-push`; `if: always() && (needs.build-and-push.result == 'success' || github.event_name == 'workflow_dispatch')`; `environment: production`; `permissions: contents: read, packages: read`): checkout; `SHA = inputs.sha || github.sha` (validar o formato); gravar a chave e o `known_hosts` em `~/.ssh` com `chmod 600`; `rsync -az --delete --exclude secrets/ deploy/ deploy@host:/opt/vocab/deploy/`; `echo "$GITHUB_TOKEN" | ssh deploy@host /opt/vocab/deploy/deploy.sh "$SHA" "${{ github.actor }}"`. No rollback, o checkout é da `main` atual, então o `compose.prod.yaml` copiado é o da `main` (documentar no runbook).
    - `dependabot.yml`: `interval: monthly`, um grupo por ecossistema: `github-actions` (`/`), `uv` (`/backend`), `npm` (`/frontend`), `docker` (`/backend` e `/frontend`).
29. **T-29** — Abrir o PR da E0; com CI verde, fazer squash merge (título `chore: add E0 walking skeleton`). Acompanhar o `deploy.yml`. Em seguida, no VPS, criar o usuário real com `create-user` (comando no runbook).
30. **T-30 (manual, você)** — Ruleset da `main`: bloquear push direto e force push, exigir PR, exigir status checks `backend`, `frontend`, `contract`, `secrets`, histórico linear, merge só por squash. (Configurado **depois** do primeiro run do CI para que os nomes dos checks apareçam na seleção.)
31. **T-31** — Validação final: critérios de sucesso 3 a 6 (instalar a PWA no celular; login/logout em produção; abrir um PR trivial e mergear para ver o deploy automático; disparar `just deploy-rollback <sha anterior>` ou o `workflow_dispatch` pela UI e confirmar `current_tag`); marcar a E0 como concluída no `delivery-plan.md`.

---

## 6. Pontos de atenção

### 6.1 Dependências entre tarefas

- **T-26 e T-27 antes do merge (T-29)**: o merge na `main` dispara o deploy; sem VPS e Environment configurados, o primeiro `deploy.yml` falha (inofensivo, mas vermelho).
- **T-16 depende de T-12** (export do OpenAPI) e da API estável; toda mudança posterior em rota/schema exige `just gen-client` (o job `contract` falha se esquecer).
- **T-30 depois de T-22/T-29**: os nomes dos checks só aparecem no ruleset depois de rodarem ao menos uma vez.
- **DNS (T-26.6) antes do primeiro deploy**: o Caddy só emite o certificado quando o domínio já aponta para o VPS; propagação no Registro.br pode levar alguns minutos.

### 6.2 Riscos técnicos

- **pytest-asyncio e escopos de loop**: o `engine` é uma fixture async de escopo `session`; testes e fixtures precisam rodar no **mesmo event loop de sessão**. Configurar `asyncio_default_fixture_loop_scope = "session"` e o equivalente para testes (o nome da opção e a sintaxe de `loop_scope` mudaram entre versões; conferir a documentação da versão instalada). Sintoma de erro: "attached to a different loop".
- **Savepoints com `commit()` nos casos de uso**: depende de `join_transaction_mode="create_savepoint"`; se algum teste vazar dados para outro, verificar se a sessão de teste está realmente ligada à conexão com a transação externa.
- **Origin no `ASGITransport`/`curl`**: o httpx não envia `Origin` sozinho; o client de teste define o header padrão. Para `curl` manual, passar `-H "Origin: ..."` em `POST`.
- **Cookie `Secure` em dev**: `SESSION_COOKIE_SECURE=false` é obrigatório em `http://localhost`; em produção o validador do `Settings` impede `false`.
- **Rate limit atrás do Caddy**: sem `--proxy-headers`, todos os requests teriam o IP do Caddy e um único limite global. Conferir nos logs de produção que o IP do cliente aparece.
- **Postgres 18**: volume em `/var/lib/postgresql` (não em `/data`); `pg_dump` da E1 deve usar a mesma major.
- **Caddy**: os volumes `caddy_data`/`caddy_config` não podem ser recriados à toa (rate limit de emissão do Let's Encrypt).
- **Imagens e GHCR**: na primeira publicação, conferir se os pacotes `vocab-api` e `vocab-web` ficaram ligados ao repositório (o `LABEL org.opencontainers.image.source` garante isso); sem a ligação, o `GITHUB_TOKEN` do job de deploy não consegue fazer `pull`.
- **Chave de deploy = acesso root ao VPS** (o usuário `deploy` está no grupo `docker`): ela só existe no Environment `production` (restrito à `main`) e pode ser revogada removendo a linha do `authorized_keys`.
- **Rollback depois de migração destrutiva**: rodar antes `IMAGE_TAG=<sha com falha> docker compose ... run --rm migrate alembic downgrade <revisão>` com a imagem que conhece a migração nova; depois reimplantar a tag anterior.
- **PWA no iOS**: a instalação é pelo menu "Adicionar à Tela de Início" do Safari; o `apple-touch-icon` é obrigatório para um ícone correto.
- **Node local**: o ambiente tem Node 24; sem a T-01, o `engines: ">=26"` e o `.nvmrc` vão divergir do CI.

### 6.3 Decisões pendentes

Nenhuma bloqueante para a E0. Itens adiados conscientemente: rodar o Caddy como não-root; restringir `--forwarded-allow-ips` à sub-rede; redirecionar logs do uvicorn para o structlog.

---

## 7. Sessões e progresso

A implementação é dividida em **cinco sessões**, executadas uma após a outra, cada uma em um contexto limpo. Cada sessão termina num marco verificável e commitado, de modo que uma falha nunca obriga a recomeçar do zero.

### 7.1 Sessões

| Sessão | Tarefas | Foco | Termina quando (marco) |
|---|---|---|---|
| **S1** — Base e backend mínimo | T-01 a T-06 | Ferramentas locais, raiz do repositório, projeto Python, app FastAPI, health, migração inicial | `just db-up` e `just migrate` funcionam; `GET /api/v1/health` → `{"status":"ok","database":"ok"}`; `alembic downgrade base` sem erro |
| **S2** — Auth no backend | T-07 a T-14 | Ports, domínio, casos de uso, endpoints de auth, CLI/seed, export do OpenAPI, testes | `just lint-backend`, `just typecheck-backend` e `just test-backend` verdes; login/me/logout funcionam pela API com o usuário de `just seed` |
| **S3** — Frontend | T-15 a T-20 | Projeto Vite, client gerado, rotas, telas, PWA, testes | Critério de sucesso 1 (login de ponta a ponta em `localhost:5173`); `just lint`, `just typecheck` e `just test` verdes |
| **S4** — CI e imagens | T-21 a T-25 | Pre-commit, `ci.yml`, Dockerfiles, Caddyfile, compose de produção, `deploy.sh`, runbook | CI verde na branch remota; as duas imagens buildam localmente; `docker compose -f deploy/compose.prod.yaml config` válido |
| **S5** — Produção | T-26 a T-31 | VPS, Environment, `deploy.yml`, merge, ruleset, validação | Critérios de sucesso 3 a 6 atendidos; E0 marcada como concluída no `delivery-plan.md` |

S1 começa com uma tarefa manual do usuário (T-01). S5 é majoritariamente manual (VPS, GitHub, ruleset): nela o agente guia o runbook e implementa apenas a T-28.

### 7.2 Protocolo de cada sessão

**Ao iniciar** (contexto limpo, via skill `scaffolding-development` indicando a sessão, ex.: "Sessão S2 do `docs/scaffolding-blueprint.md`"):

1. Ler esta seção (7.3 e 7.4) e o `git log --oneline` da branch `chore/e0-walking-skeleton`.
2. Confirmar que o marco da sessão anterior continua valendo (rodar as verificações da linha correspondente em 7.1). Se não valer, corrigir antes de seguir.
3. Ler no registro (7.4) os desvios e descobertas das sessões anteriores; eles prevalecem sobre o texto das seções 2–4 deste documento.
4. Executar apenas as tarefas da sessão, na ordem da seção 5. Não adiantar tarefas da sessão seguinte.

**Durante**: um commit por tarefa (ou por grupo pequeno de tarefas), sempre com aprovação explícita do usuário antes de cada commit (`CLAUDE.md`).

**Ao terminar**:

1. Rodar as verificações do marco (7.1) e reportar o resultado ao usuário.
2. Atualizar a tabela 7.3 (status e commit de cada tarefa).
3. Acrescentar uma entrada em 7.4 com: data, tarefas concluídas, **desvios do Blueprint** (com o motivo), versões fixadas que importam para as próximas sessões, problemas em aberto e o próximo passo.
4. Incluir essa atualização no último commit da sessão.

Se uma sessão não chegar ao marco, registrar mesmo assim em 7.4 o ponto exato onde parou; a próxima sessão retoma dali.

### 7.3 Progresso por tarefa

Status: ⬜ pendente · 🔄 em andamento · ✅ concluída · ⏭️ pulada (explicar em 7.4).

| Sessão | Tarefa | Descrição | Status | Commit |
|---|---|---|---|---|
| S1 | T-01 | Ferramentas locais (manual) | ✅ | — (manual) |
| S1 | T-02 | Base do repositório | ✅ | `b701a15` |
| S1 | T-03 | Projeto Python | ✅ | `1266344` |
| S1 | T-04 | Config, logging, app | ✅ | `13012a8` |
| S1 | T-05 | Base ORM, engine, health | ✅ | `13012a8` |
| S1 | T-06 | Modelos e migração inicial | ✅ | commit final da S1 |
| S2 | T-07 | Ports, adapters e fakes | ✅ | `6dd412b` |
| S2 | T-08 | Domínio de auth + testes unitários | ✅ | `6dd412b` |
| S2 | T-09 | Casos de uso de auth | ✅ | `241dcef` |
| S2 | T-10 | Camada HTTP de auth | ✅ | `241dcef` |
| S2 | T-11 | CLI create-user e seed-dev | ✅ | `489fc49` |
| S2 | T-12 | Exportação do OpenAPI | ✅ | `489fc49` |
| S2 | T-13 | Fixtures de teste | ✅ | commit final da S2 |
| S2 | T-14 | Testes de integração e API | ✅ | commit final da S2 |
| S3 | T-15 | Projeto frontend e ferramentas | ✅ | `f01ada0` |
| S3 | T-16 | Client da API | ✅ | `2a3e88d` |
| S3 | T-17 | Router e rotas | ✅ | `2a3e88d` |
| S3 | T-18 | Telas e features | ✅ | `2a3e88d` |
| S3 | T-19 | PWA | ✅ | `6fdfb67` |
| S3 | T-20 | Testes de frontend | ✅ | commit final da S3 |
| S4 | T-21 | Pre-commit | ✅ | `fd0be84` |
| S4 | T-22 | CI | ✅ | `b1085b5`, `15d9f48` |
| S4 | T-23 | Imagem api | ✅ | `9466871` |
| S4 | T-24 | Imagem web e Caddyfile | ✅ | `9466871` |
| S4 | T-25 | Compose de produção, deploy.sh, runbook | ✅ | commit final da S4 |
| S5 | T-26 | Configuração do VPS (manual) | ✅ | — (manual); runbook em `71386b9` |
| S5 | T-27 | Environment do GitHub (manual) | ✅ | — (manual) |
| S5 | T-28 | deploy.yml e Dependabot | ✅ | commit da T-28 |
| S5 | T-29 | PR, merge e primeiro deploy | ✅ | `fab790c` (PR #2) |
| S5 | T-30 | Ruleset da main (manual) | ⬜ | |
| S5 | T-31 | Validação final | ⬜ | |

### 7.4 Registro de sessões

> Uma entrada por sessão, mais recente por último. Modelo:
>
> **S<n> — AAAA-MM-DD**
> - **Concluído:** T-xx a T-yy.
> - **Desvios do Blueprint:** o que mudou e por quê (ou "nenhum").
> - **Versões e decisões práticas:** versões fixadas, opções de configuração descobertas.
> - **Em aberto:** problemas conhecidos, verificações que falharam.
> - **Próximo passo:** primeira ação da próxima sessão.

**S1 — 2026-11-12**
- **Concluído:** T-01 a T-06. Marco verificado: `just db-up` (Postgres saudável), `just migrate`, `GET /api/v1/health` → `200 {"status":"ok","database":"ok"}` (e `503` com o banco parado), `alembic downgrade base` sem erro, `alembic check` sem drift, `ruff`/`mypy` verdes.
- **Desvios do Blueprint:**
  - **Node padrão do sistema continua 24.18.0** (`nvm alias default 24.18.0`, em vez de `nvm alias default 26`): o Claude Code e outro projeto local (QuickSilver) usam o Node 24 global. O Node 26.13.1 está instalado e é usado só neste projeto (`nvm use` na pasta `frontend/`, via `.nvmrc`). Nas receitas do `just` que chamam o frontend (S3), garantir Node 26 no PATH.
  - **`POSTGRES_PORT` passou a definir a porta do host no `compose.yaml`** (`127.0.0.1:${POSTGRES_PORT:-5432}:5432`): a 5432 está ocupada pelo Postgres do QuickSilver. O `.env` local usa **5433**; o `.env.example` mantém 5432.
  - **Nova configuração `API_PORT`** (default 8000; `.env` local **8001**, porque a 8000 é do backend do QuickSilver): usada por `just dev-backend` e por `Settings.allowed_origins` em dev (`http://localhost:{api_port}`). **Na S3, o proxy do Vite deve apontar para `http://localhost:${API_PORT}`**, e o `curl` manual com `Origin` deve usar a porta do `.env`.
  - `InMemoryRateLimiter` (com `time_func` injetável) criado na T-04, porque o `create_app()` já o instancia; os testes dele seguem na S2.
  - `just setup` usa `[ -f .env ] || cp .env.example .env` em vez de `cp -n` (o GNU coreutils emite aviso de não-portável). Ainda não roda `pnpm install` (frontend nasce na S3) nem pre-commit (T-21).
  - `alembic.ini` mantém `script_location = %(here)s/migrations` (padrão do Alembic 1.20, funciona de qualquer diretório) e `migrations/script.py.mako` foi reescrito com tipos modernos (`str | None`, `collections.abc`) para passar no ruff.
  - O `README.md` foi criado e entrou no commit da T-06 (em vez da T-02), para só citar receitas que já existem.
- **Versões e decisões práticas:** Python 3.14.7; Node 26.13.1 (LTS Lithium); pnpm 12.18.0 (standalone); just 1.59.0; `postgres:18.7-alpine`; FastAPI 0.162.5, SQLAlchemy 2.1.8, pydantic 2.14.3, pydantic-settings 2.16.2, Alembic 1.20.1, psycopg 3.3.9, structlog 26.1.0, uvicorn 0.54.0, pytest 9.2.0, pytest-asyncio 1.5.0 (opções `asyncio_default_fixture_loop_scope` e `asyncio_default_test_loop_scope`, ambas `session`), mypy 2.4.1, ruff 0.17.5, testcontainers 4.15.0. O parser de dotenv do `just` remove comentários inline do `.env` corretamente. O PostgreSQL 18 registra NOT NULL como constraints nomeadas (`<tabela>_<coluna>_not_null`); não afeta o Alembic. **Rede corporativa com inspeção TLS (Cato Networks):** `curl` falha com "self-signed certificate"; o Node já usa `NODE_EXTRA_CA_CERTS=~/cato-ca.cer`. Para downloads com `curl`, usar `CURL_CA_BUNDLE` apontando para o bundle do sistema + `~/cato-ca.cer`. Na S4, builds Docker que baixam pacotes podem precisar do mesmo tratamento.
- **Em aberto:** `verify_origin` ainda não tem rota POST para ser exercitado (fica coberto pelos testes de API da S2). `gh` não instalado (opcional, só para `just deploy-rollback`).
- **Próximo passo:** S2, começando pela T-07 (ports `Clock`/`PasswordHasher`, adapters e fakes).

**S2 — 2026-11-13**
- **Concluído:** T-07 a T-14. Marco verificado: `just lint-backend`, `just typecheck-backend` e `just test-backend` verdes (33 testes, 0 warnings, cobertura 81%); `just seed` idempotente (e recusado com `APP_ENV=production`); login → `/me` → logout pela API com `curl` na porta 8001 (`Origin: http://localhost:8001`), incluindo `401` genérico, `403` sem `Origin` e `401` com o cookie antigo após o logout.
- **Desvios do Blueprint:**
  - **Senha mínima de 8 caracteres** (em vez de 12), a pedido do usuário (`MIN_PASSWORD_LENGTH` em `application/auth/create_user.py`).
  - Nova exceção `InvalidUserInput(ValueError)` em `application/auth/errors.py` para e-mail/senha fora das regras (a 2.8 não nomeava o erro de validação).
  - `DUMMY_HASH` cacheado **por tipo de hasher** (`dict[type, str]`), para não verificar um hash fake com o Argon2 (ou o contrário) quando ambos existem no mesmo processo.
  - `test_settings` fixa `api_port=8000` (e os demais campos de sessão): o `just` exporta o `.env` local (`API_PORT=8001`) e o `Origin` do client de teste deixaria de ser aceito.
  - `logout` usa `delete_cookie` com os mesmos atributos do `set_cookie` (`httponly`, `secure`, `samesite`).
  - Testes além da lista da 4.2–4.4: `tests/unit/test_argon2_hasher.py` (adapter real), `tests/integration/test_create_user.py` (normalização, mínimo de 8, e-mail inválido, duplicado), `test_logout_without_session_returns_204` e `test_session_is_renewed_after_one_hour` (variação prevista na 3.5).
  - Receitas agregadas `lint`, `typecheck`, `test` e `format` ainda não existem: dependem do frontend (S3). Por ora há só as `*-backend` e `test-unit/integration/api`.
- **Versões e decisões práticas:** testcontainers 4.15: importar de `testcontainers.community.postgres` (o caminho `testcontainers.postgres` emite `DeprecationWarning`). SQLAlchemy 2.1: `Row` se desempacota direto (`session, user = row`); `row.tuple()`/`row._tuple()` estão depreciados. httpx: cookies por request (`cookies=...`) estão depreciados; usar `client.cookies.set(...)`. O marker de cada teste vem da pasta (`pytest_collection_modifyitems` no `tests/conftest.py`), então `pytest -m unit` roda sem Docker. Um container `postgres:18.7-alpine` por sessão de testes (~5 s).
- **Em aberto:** o cookie de sessão tem `Max-Age` fixo de 60 dias a partir do login, enquanto o servidor renova `expires_at` (expiração deslizante). Um usuário ativo terá o cookie expirado no navegador após 60 dias mesmo com a sessão válida no banco. Decidir se o `current_user` deve reemitir o cookie quando a sessão é renovada.
- **Próximo passo:** S3, começando pela T-15 (projeto Vite). Proxy do Vite para `http://localhost:${API_PORT}` (8001 no `.env` local) e `just gen-client` usando `uv run python -m app.scripts.export_openapi`.

**S3 — 2026-11-13**
- **Concluído:** T-15 a T-20. Marco verificado: login de ponta a ponta no navegador em `localhost:5173` (validado pelo usuário: redirect para `/login`, login, "API: ok · Banco: ok", e-mail no cabeçalho, "Sair"); o mesmo fluxo por `curl` pelo proxy do Vite (`Origin: http://localhost:5173` aceito pelo backend sem mudanças); `just lint`, `just typecheck` e `just test` verdes (backend: 33 testes, 81%; frontend: 13 testes, sem avisos); `just build-frontend` gera `sw.js` e `manifest.webmanifest` (precache de 29 entradas, nenhuma rota de runtime, `/api/` fora do fallback de navegação).
- **Desvios do Blueprint:**
  - **TypeScript fixado em `~6.0.3`** (decisão do usuário): o `create-vite` 9.3 já vem com TypeScript 7 (nativo) e oxlint, mas o `typescript-eslint` 8.72 aceita só `<6.1` e o `openapi-typescript` 7.13 declara `^5.x`. O oxlint foi removido para seguir a spec (ESLint flat). Revisitar quando o `typescript-eslint` suportar o TS 7.
  - **Node 26 via `devEngines.runtime`** no `package.json` (`onFail: "download"`): o pnpm baixa o Node 26.13.1 para o `node_modules` e roda scripts/`exec` com ele, mesmo com o Node 24 como padrão do sistema. As receitas do `just` não usam nvm. O `.nvmrc` continua (CI e editor).
  - **`libatomic1`** instalada no WSL: o binário do Node 26 depende dela e o Ubuntu 24.04 do WSL não a traz (o Node 26 da S1 nunca tinha chegado a rodar). Documentado no README.
  - **Proxy do Vite lê `API_PORT`** do `.env` da raiz (`loadEnv`), em vez de fixar `localhost:8000`. `server.strictPort: true`.
  - **shadcn 4.23** (`-b base -p nova` → estilo `base-nova`, Base UI): `cn()` vem do pacote oficial `cn` (substitui `clsx` + `tailwind-merge`); fonte Geist via `@fontsource-variable/geist`.
  - **`ApiError(status, body)`**: o `openapi-react-query` lança só o corpo do erro, sem o status. Um middleware do `fetchClient` lança `ApiError` em toda resposta não-2xx; `isUnauthorized`, `LoginForm` e `HealthStatus` usam `error.status`. O redirect por 401 é um handler registrado pelo `router.ts` (`setUnauthorizedHandler`), evitando import circular `client.ts` ↔ `router.ts`.
  - **`fetch: (request) => globalThis.fetch(request)`** no `createFetchClient`: o `openapi-fetch` captura o `fetch` na criação do client, antes do `server.listen()` do MSW. Sem isso, os testes iam para a rede de verdade (no caso, o `just dev` aberto) em vez dos handlers.
  - **MSW 3**: a opção do `listen()` agora é `onUnhandledFrame: "error"` (era `onUnhandledRequest`). Respostas cujo corpo não está no OpenAPI (401/429 do FastAPI) usam `response.untyped(...)` no openapi-msw. `msw/node` fica em `src/test/server.ts`.
  - **TanStack Query 5.107**: `ensureQueryData` está depreciado; o `_authenticated` usa `queryClient.query({ ...meQueryOptions(), staleTime: "static" })` (mesma semântica).
  - **React 19.3**: `FormEvent` depreciado; o `LoginForm` usa `SubmitEvent`.
  - **ESLint**: `react-refresh/only-export-components` desligada em `src/routes/` (arquivos de rota só exportam `Route`; o HMR deles é do plugin do router). `typescript-eslint` com `strictTypeChecked` + `stylisticTypeChecked`. `redirect` do TanStack Router lançado com `eslint-disable-next-line @typescript-eslint/only-throw-error`.
  - **Prettier** com `printWidth: 100`.
  - **`routeTree.gen.ts` versionado** (gerado pelo plugin no `vite dev`/`vite build`; o `tsc -b` precisa dele).
  - **`isSafeRedirect`** (`features/auth/safe-redirect.ts`) recusa também `/\` além de `//`; ganhou teste próprio. O `login` e o `beforeLoad` usam `redirect({ href })`/`navigate({ href })`, já que o destino é um caminho livre.
  - **PWA**: ícone próprio (`favicon.svg` com "V"; o do template era o logo do Vite); o gerador também cria `favicon.ico`; `globPatterns` inclui `ico` e `woff2` (fonte no precache).
  - **Receitas novas**: `dev`, `dev-frontend`, `build-frontend`, `gen-client` (com `trap` para apagar o temporário), `lint-frontend`, `typecheck-frontend` (`tsc -b`), `test-frontend` e as agregadas `lint`, `typecheck`, `test`, `format`. `just setup` passou a rodar `pnpm install`. `just build` (com Docker) fica para a S4.
- **Versões e decisões práticas:** create-vite 9.3.4; Vite 8.3; React 19.3; TypeScript 6.0.3; TanStack Router 1.170 (plugin 1.169), TanStack Query 5.107; openapi-fetch 0.17, openapi-react-query 0.5, openapi-typescript 7.13; Tailwind 4.3; shadcn 4.23; vite-plugin-pwa 2.0 (+ `workbox-window`), `@vite-pwa/assets-generator` 2.0; Vitest 5.1, jsdom 31, MSW 3.0, openapi-msw 2.1, Testing Library (React 16.3, jest-dom 7); ESLint 10.14, typescript-eslint 8.72, react-hooks 7.1, react-refresh 0.5; Prettier 3.10; `@types/node` 26. Vitest 5 esconde `console.log` de testes que passam (usar `--silent=false` para depurar).
- **Em aberto:** a instalação da PWA no celular só é validável com HTTPS (S5). Continua em aberto o `Max-Age` fixo do cookie (S2). Os componentes de `src/components/ui/` usam `next-themes` (vindo do shadcn) sem `ThemeProvider`; o `useTheme` cai em `"system"`, que é o comportamento desejado por ora.
- **Próximo passo:** S4, começando pela T-21 (pre-commit). No CI (T-22), o job `frontend` pode usar o Node do `setup-node` (`frontend/.nvmrc`); o `devEngines.runtime` faz o pnpm baixar a mesma versão se divergir. O `contract` roda `just gen-client` e `git diff --exit-code frontend/src/api/`.

**S4 — 2026-11-13**
- **Concluído:** T-21 a T-25. Marco verificado: `uvx pre-commit run --all-files` verde; CI verde na branch remota (`backend`, `frontend`, `contract`, `secrets`); `just build` gera `vocab-api:local` (307 MB) e `vocab-web:local` (93 MB); `docker compose -f deploy/compose.prod.yaml config` válido com variáveis fictícias. Além do marco: a stack de produção subiu localmente (cópia de `deploy/` com `.env` de produção fictício, portas remapeadas e `APP_DOMAIN=localhost` com a CA interna do Caddy): `migrate` aplicou a `0001` e saiu com 0; `create-user` via `run --rm api`; login → `/me` por HTTPS pelo Caddy, com cookie `Secure` e HSTS; fallback da SPA; HTTP → 308 para HTTPS; o uvicorn usa o IP do `X-Forwarded-For`.
- **Desvios do Blueprint:**
  - **Caddyfile, cache do `index.html`:** o `header` roda antes do `try_files`, então `@sw path /sw.js /index.html /manifest.webmanifest` não pegava as navegações da SPA (`/`, `/login`), que voltavam sem `Cache-Control`. Agora `@revalidate not path /assets/*` + `header @revalidate ?Cache-Control "no-cache"` (o `?` preserva o header da `api`, se houver). Spec §11.2 atualizada.
  - **Permissão do secret:** sem Swarm, o secret do Compose é um bind mount que preserva dono e modo do host, e a `api` roda como uid 1000. Com `chmod 600` e dono `deploy`, a leitura só funciona se o `deploy` tiver uid 1000. Regra adotada: `secrets/` com `chmod 700` e dono `deploy`; `postgres_password` com `chmod 444`. Spec §5.4 e §11.6 e runbook atualizados.
  - **`check-yaml` exclui `frontend/pnpm-lock.yaml`:** o lockfile do pnpm 12 tem vários documentos YAML. Os arquivos gerados (`routeTree.gen.ts`, `schema.d.ts`) ficam fora de todos os hooks.
  - **Hooks do frontend:** dois hooks locais (`eslint --no-warn-ignored` e `prettier --write --ignore-unknown`), com o prefixo `frontend/` removido dos caminhos por `bash -c '... "${@#frontend/}"' --`.
  - **`astral-sh/setup-uv@v10.3.3`:** a action não publica tag maior flutuante (`@v10` quebrou o primeiro run). As demais usam tag maior (`checkout@v7`, `setup-node@v7`, `pnpm/action-setup@v6`, `extractions/setup-just@v4`, `upload-artifact@v7`, `gitleaks-action@v3`).
  - **CI:** `concurrency` cancela runs antigos fora da `main`; o job `secrets` tem `pull-requests: read` (a action lista os commits do PR) e `GITLEAKS_ENABLE_COMMENTS: false`; a cobertura sobe como artefato `backend-coverage`; `persist-credentials: false` nos checkouts.
  - **`deploy.sh`:** o `docker logout` fica num `trap EXIT` (cobre sucesso e falha); `APP_DOMAIN` é lido do `.env` com `grep` (sem `source`); a limpeza de imagens usa `docker image ls ... | sort -r | tail -n +3`.
  - `backend/Dockerfile` copia também o `.python-version`; `frontend/.dockerignore` ignora ainda `.tanstack/`, `Dockerfile` e `.dockerignore`.
  - **Receita `just build`** adicionada. **`just deploy-rollback`** fica para a S5, junto com o `deploy.yml` que ela dispara (o runbook já a cita).
- **Versões e decisões práticas:** `python:3.14.10-slim`, `ghcr.io/astral-sh/uv:0.12.13`, `node:26.13.1-slim` (pnpm 12.18.0 via `npm install -g`), `caddy:2.11.9-alpine`, `postgres:18.7-alpine`; pre-commit 4.7.0 com pre-commit-hooks v6.0.0, ruff-pre-commit v0.17.5 e gitleaks v8.30.1 (a mesma versão no CI, via `GITLEAKS_VERSION`); Docker Compose v5.1.3 (aceita `!override` em arquivos de override). O build das imagens funcionou através do proxy TLS da Cato sem ajustes (houve só um timeout passageiro do npm, que se recuperou sozinho). O repositório é **privado**: a API pública do GitHub responde 404 e o status do CI é conferido pela interface web (ou com `gh`, ainda não instalado).
- **Em aberto:** a permissão `444` do secret foi validada só com uid 1000 local; confirmar no VPS (S5) que a `api` lê `/run/secrets/postgres_password` com o uid real do `deploy`. Continuam em aberto o `Max-Age` fixo do cookie (S2) e a validação da PWA no celular (S5).
- **Próximo passo:** S5. T-26 (VPS, seguindo `deploy/README.md` §1) e T-27 (Environment `production`, §2) são manuais. Depois, a T-28 (`deploy.yml` + `dependabot.yml` + receita `deploy-rollback`).

**S5 — 2026-11-23 (em andamento)**
- **Concluído até agora:** T-26 e T-27 (manuais, validados pelo usuário) e T-28 (validada com actionlint; a validação real é o primeiro deploy, na T-29). O DNS `vocab.gbs-software.com.br` resolve para a VPS. O certificado Let's Encrypt foi emitido pelo Caddy do host, e o domínio responde `502` até o primeiro deploy, como esperado. As stacks do GBS seguiram no ar. O SSH com a chave `vocab-deploy` funciona como `deploy`, com o grupo `docker`. A fingerprint do `ssh-keyscan` confere com a do host. Environment `production` criado (só `main`), com `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `DEPLOY_KNOWN_HOSTS` e a variável `APP_DOMAIN`. O plano do GitHub suporta Environments em repositório privado.
- **Desvios do Blueprint:**
  - **VPS compartilhada com o GBS Ops Flow** (Ubuntu 26.04, operada como `root`, Docker e Caddy já instalados). O Caddy do host já ocupava as portas 80/443. **ADR 0013** (`71386b9`): o TLS fica com o Caddy do host, e o `web` atende só HTTP em `127.0.0.1:9001` (`auto_https off`, `trusted_proxies static private_ranges`). O compose ganhou `name: vocab` e perdeu os volumes `caddy_data`/`caddy_config`. Validado localmente com um Caddy simulando o do host: login por HTTPS, cookie `Secure`, IP real chegando à `api` e `X-Forwarded-For` forjado ignorado. Spec (§1.4, §11.2, §11.4, §11.6), ADR 0001, `AGENTS.md`, overview e runbook atualizados. Isso substitui os itens 1–3 e 6 da T-26 na seção 5.
  - **Domínio:** `vocab.gbs-software.com.br` (zona já existente no Registro.br).
  - **Hardening da VPS fora do escopo** (decisão do usuário): firewall e SSH são pendências do guia da VPS compartilhada, fora do runbook do vocab.
  - O registro no guia da VPS (`GUIA-VPS.md`, fora do repositório) contém só o estado da máquina, nada do fluxo do projeto.
  - Nova convenção no `AGENTS.md` (`b262995`): só comentários estritamente necessários.
  - **`deploy.yml`:** `build-and-push` usa uma `matrix` (`vocab-api`/`backend`, `vocab-web`/`frontend`), em vez de dois passos no mesmo job: as imagens são construídas em paralelo, com `scope` de cache próprio. O job `ci` repassa `pull-requests: read`, porque o reusable workflow só recebe permissões que o chamador concede, e o job `secrets` do `ci.yml` precisa dela. Há `permissions: {}` no topo, e cada job declara as suas. O `deploy` usa `!cancelled()` em vez de `always()`, para não implantar um run cancelado. Os secrets chegam aos passos por `env` e nunca interpolados no script. O SSH usa um alias `vps` em `~/.ssh/config` com `StrictHostKeyChecking yes`.
  - **`dependabot.yml`:** prefixos de commit no padrão Conventional Commits (`ci` para actions; `build(deps)` para os demais). Na imagem `python`, ignora atualizações minor e major (3.15 bloqueado pelo spaCy, ADR 0004). Na `node`, ignora major (só LTS, ADR 0005). O compose de produção (`postgres`) fica fora, como na spec: um salto de major do Postgres exige dump/restore.
- **Versões e decisões práticas:** `docker/setup-buildx-action@v4`, `docker/login-action@v4`, `docker/build-push-action@v7`. A receita `just deploy-rollback <sha>` requer o `gh` autenticado, que ainda não está instalado localmente; a alternativa é a UI (Actions → Deploy → Run workflow). Porta `9001` reservada para o vocab (faixa 9001+ do guia da VPS). Docker Engine 29.10 e Compose v5.7.1 na VPS. Caddy do host 2.11.9. O backup do Caddyfile anterior ficou em `/etc/caddy/Caddyfile.bak-<data>`.
- **Em aberto:** confirmar no primeiro deploy que a `api` lê `/run/secrets/postgres_password` (`444`) com o uid real do `deploy`. Continuam em aberto o `Max-Age` fixo do cookie (S2) e a PWA no celular (T-31).
- **T-29 concluída:** PR #2 com CI verde e squash merge (`fab790c`). O primeiro `deploy.yml` passou (`ci` → `build-and-push` em paralelo → `deploy` em 36 s; o smoke test passou na 2ª tentativa, com a api ainda iniciando). Conferido de fora: `/api/v1/health` → `{"status":"ok","database":"ok"}`, o que confirma que a `api` lê o secret `444` com o uid real do `deploy`; `/login` com HSTS e `no-cache`; HTTP → `308`. Usuário real criado com `create-user`, e o login em produção foi validado pelo usuário.
- **Ajustes após o primeiro deploy** (PR seguinte, que também serve de "PR trivial" da T-31): `cache-dependency-glob: uv.lock` no `ci.yml` (o caminho é relativo ao `working-directory: backend`; com `backend/uv.lock` o cache nunca invalidava). `DEPLOY_USER` passou de secret a variável do Environment: o GitHub mascarava como `***` toda ocorrência de "deploy" nos logs.
- **Próximo passo:** T-30 (ruleset da `main`) e T-31 (PWA no celular, deploy por PR trivial, rollback, E0 concluída no `delivery-plan.md`).
