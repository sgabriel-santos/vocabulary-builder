# Architecture Decision Records

Decisões arquiteturais do Vocabulary Builder. Formato curto: Status, Data, Contexto, Decisão, Consequências. Nome: `NNNN-titulo-em-kebab-case.md`, numeração sequencial. Uma decisão substituída recebe o status `Substituída por NNNN`.

| ADR | Título | Status |
|---|---|---|
| [0001](0001-hosting-vps-compose-caddy.md) | Hospedagem em VPS com Docker Compose e Caddy | Aceita |
| [0002](0002-postgres-on-vps-with-offsite-backup.md) | Postgres em container no VPS com backup externo | Aceita |
| [0003](0003-auth-password-server-side-sessions.md) | Autenticação por senha com sessão server-side | Aceita |
| [0004](0004-python-tooling-uv-python-314.md) | Ferramentas Python: uv e Python 3.14 | Aceita |
| [0005](0005-frontend-tooling-pnpm-node-26.md) | Ferramentas do frontend: pnpm e Node 26 LTS | Aceita |
| [0006](0006-persistence-sqlalchemy-psycopg-domain-separation.md) | Persistência: SQLAlchemy 2.0 async, psycopg 3 e separação domínio × ORM | Aceita |
| [0007](0007-backend-testing-testcontainers.md) | Estratégia de testes do backend com testcontainers | Aceita |
| [0008](0008-frontend-routing-tanstack-router.md) | Roteamento do frontend com TanStack Router | Aceita |
| [0009](0009-api-client-openapi-fetch-versioned.md) | Client da API gerado com openapi-typescript e openapi-fetch | Aceita |
| [0010](0010-docker-images-and-compose-layout.md) | Imagens Docker e organização do Compose | Aceita |
| [0011](0011-ci-cd-auto-deploy-with-rollback.md) | CI/CD com GitHub Actions, deploy automático e rollback manual | Aceita |
| [0012](0012-branching-pr-squash-merge.md) | Branching com PR e squash merge | Aceita |

## Template

```markdown
# NNNN — Título

- **Status:** Proposta | Aceita | Substituída por NNNN
- **Data:** AAAA-MM-DD

## Contexto

O problema e as forças em jogo.

## Decisão

O que foi decidido.

## Consequências

Efeitos positivos, negativos e o que passa a ser obrigatório.
```
