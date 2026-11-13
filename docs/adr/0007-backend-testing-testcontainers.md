# 0007 — Estratégia de testes do backend com testcontainers

- **Status:** Aceita
- **Data:** 2026-11-12

## Contexto

Os requisitos exigem testes unitários do domínio (com relógio injetável), testes de integração/endpoint, fakes para todos os provedores e nenhum teste chamando APIs pagas. Usamos recursos específicos do Postgres (JSONB, constraints), então SQLite não serve. Opções para o banco dos testes: testcontainers ou Postgres do compose com banco separado.

## Decisão

- Pastas: `tests/unit` (sem banco, com fakes), `tests/integration` (migrações, constraints e, quando existirem, repositórios em Postgres real), `tests/api` (app completo via `httpx.AsyncClient` + `ASGITransport`, banco real, provedores fake via `dependency_overrides`), `tests/fakes` (fakes dos ports de provedores e infraestrutura, como `Clock` e `PasswordHasher`). Repositórios **não** ganham fake em memória por padrão: os testes de integração e de API já usam Postgres real, e a regra de negócio fica em código puro de `domain/`. Um fake de repositório só é criado quando um teste unitário realmente precisar dele. Markers `unit`, `integration`, `api`.
- Port `Clock` desde a E0.
- Postgres via **testcontainers** (`postgres:18-alpine`, mesma imagem da produção), `alembic upgrade head` uma vez por sessão e rollback por teste (savepoint, `join_transaction_mode="create_savepoint"`).
- pytest + pytest-asyncio (modo auto) + pytest-cov sem gate de cobertura na E0.

## Consequências

- Comportamento idêntico no WSL e no CI, sem passo manual; migrações testadas a cada execução.
- Exige Docker rodando para testes de integração/API (~3–5 s de inicialização); testes unitários continuam instantâneos.
