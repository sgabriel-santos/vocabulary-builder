# 0011 — CI/CD com GitHub Actions, deploy automático e rollback manual

- **Status:** Aceita
- **Data:** 2026-11-12

## Contexto

O critério de pronto da E0 exige que um push na `main` publique automaticamente. A Action terá acesso SSH ao VPS, então o deploy precisa ser seguro. O projeto é single-user e sem SLA: alguns minutos fora do ar são aceitáveis. O rollback automático foi considerado e descartado por enquanto, porque obrigaria todas as migrações a seguir expand/contract (o rollback volta o código, não o schema), um custo permanente sem benefício proporcional.

## Decisão

- **`ci.yml`** em PRs e pushes fora da `main` (e reutilizável via `workflow_call`): lint, type check e testes do backend (com testcontainers) e do frontend, checagem de drift do client OpenAPI e gitleaks. Os jobs chamam receitas `just`.
- **`deploy.yml`** em push na `main`, num único workflow com jobs encadeados por `needs` (sem `workflow_run`): CI reutilizado → build e push das imagens no GHCR → cópia de `deploy/` → `deploy.sh <sha>` via SSH → smoke test em `/api/v1/health`. Se o smoke test falhar, o job fica vermelho.
- **Rollback manual**: `workflow_dispatch` com input `sha` reimplanta uma tag já publicada (`just deploy-rollback <sha>`).
- Segurança: Environment `production` com `known_hosts` fixado e *deployment branch rule* restrita à `main`; chave SSH exclusiva do deploy para o usuário `deploy` (grupo `docker`, sem sudo), **sem** `command=`; login no GHCR com `GITHUB_TOKEN` efêmero; `concurrency: production`; permissões mínimas por job.
- **Dependabot** mensal, agrupado (actions, uv, npm, docker).

## Consequências

- A `main` é o que está em produção; um deploy com falha fica visível (job vermelho) e é revertido manualmente com um comando.
- Migrações compatíveis com a versão anterior são **diretriz**, não regra. Depois de uma migração destrutiva, o rollback exige `alembic downgrade` antes de reimplantar a tag anterior.
- Rollback automático pode ser reavaliado quando houver dados ou uso que o justifiquem.
- Como o usuário `deploy` está no grupo `docker` e o compose de produção chega do CI, uma chave de deploy vazada equivale a acesso root ao VPS. A proteção está no acesso à chave (Environment restrito à `main`, chave exclusiva e revogável). Restringir a chave por `command=` só protegeria com `deploy.sh` e compose fixos no servidor, o que tiraria do CI as mudanças no compose; a primeira versão desta ADR combinava `command=` com a cópia de `deploy/`, o que não funciona.
