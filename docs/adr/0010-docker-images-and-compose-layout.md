# 0010 — Imagens Docker e organização do Compose

- **Status:** Aceita
- **Data:** 2026-11-12

## Contexto

Produção em VPS com Compose e Caddy (ADR 0001); requisito de portabilidade via containers; dev rápido com hot reload. Decisão tomada com apoio da skill `docker-advisor`.

## Decisão

- **Imagem `api`**: multi-stage `python:3.14-slim` + uv (versão fixa), runtime não-root, healthcheck em Python. A mesma imagem roda API, migrações, CLI e (a partir da E2) worker. Base slim (glibc) em vez de Alpine/distroless por causa de libs nativas.
- **Imagem `web`**: build do SPA em `node:26-slim` + pnpm → `caddy:2.x-alpine` com Caddyfile e `dist/`.
- **Dois arquivos Compose independentes**: `compose.yaml` (dev: só Postgres em `127.0.0.1`; backend e frontend nativos) e `deploy/compose.prod.yaml` (`web`, `api`, `migrate`, `db`).
- Migrações por serviço one-off `migrate`; a `api` só sobe após `migrate` concluir com sucesso.
- Imagens no GHCR com tag = SHA do commit (nunca `latest`).
- Segredos sensíveis via Compose `secrets:` (`/run/secrets`), configuração não sensível no `.env` do servidor.
- Limites de CPU/memória por serviço, `restart: unless-stopped`, rotação de logs, volume `caddy_data` obrigatório, `docker.sock` nunca montado.

## Consequências

- Uma imagem a menos para manter; rollback trocando a tag.
- `up -d` sempre migra antes de subir a nova API; se a migração falhar, a API anterior continua no ar.
- Dev e prod com arquivos legíveis isoladamente, ao custo de alguma repetição.
