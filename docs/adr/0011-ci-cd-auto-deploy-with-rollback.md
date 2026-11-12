# 0011 — CI/CD com GitHub Actions, deploy automático e rollback

- **Status:** Aceita
- **Data:** 2026-11-12

## Contexto

O critério de pronto da E0 exige que um push na `main` publique automaticamente. A Action terá acesso SSH ao VPS, então o deploy precisa ser seguro.

## Decisão

- **`ci.yml`** em todo push/PR: lint, type check e testes do backend (com testcontainers) e do frontend, checagem de drift do client OpenAPI e gitleaks. Os jobs chamam receitas `just`.
- **`deploy.yml`** automático na `main` com CI verde: build e push das imagens no GHCR → cópia de `deploy/` → `deploy.sh <sha>` via SSH → smoke test em `/api/v1/health` → **rollback automático** para a tag anterior se falhar.
- Segurança: Environment `production` com `known_hosts` fixado; usuário `deploy` com chave restrita por `command=` ao `deploy.sh`; login no GHCR com `GITHUB_TOKEN` efêmero; `concurrency: production`; permissões mínimas por job.
- **Dependabot** semanal, agrupado (actions, uv, npm, docker).

## Consequências

- A `main` é sempre o que está em produção; falhas de deploy se recuperam sozinhas.
- O rollback não reverte migrações: migrações devem ser compatíveis com a versão anterior (expand/contract).
- Uma chave de deploy vazada só consegue executar o `deploy.sh`.
