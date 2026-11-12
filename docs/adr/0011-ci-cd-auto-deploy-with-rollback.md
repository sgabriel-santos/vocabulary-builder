# 0011 — CI/CD com GitHub Actions, deploy automático e rollback manual

- **Status:** Aceita
- **Data:** 2026-11-12

## Contexto

O critério de pronto da E0 exige que um push na `main` publique automaticamente. A Action terá acesso SSH ao VPS, então o deploy precisa ser seguro. O projeto é single-user e sem SLA: alguns minutos fora do ar são aceitáveis. O rollback automático foi considerado e descartado por enquanto, porque obrigaria todas as migrações a seguir expand/contract (o rollback volta o código, não o schema), um custo permanente sem benefício proporcional.

## Decisão

- **`ci.yml`** em PRs e pushes fora da `main` (e reutilizável via `workflow_call`): lint, type check e testes do backend (com testcontainers) e do frontend, checagem de drift do client OpenAPI e gitleaks. Os jobs chamam receitas `just`.
- **`deploy.yml`** em push na `main`, num único workflow com jobs encadeados por `needs` (sem `workflow_run`): CI reutilizado → build e push das imagens no GHCR → cópia de `deploy/` → `deploy.sh <sha>` via SSH → smoke test em `/api/v1/health`. Se o smoke test falhar, o job fica vermelho.
- **Rollback manual**: `workflow_dispatch` com input `sha` reimplanta uma tag já publicada (`just deploy-rollback <sha>`).
- Segurança: Environment `production` com `known_hosts` fixado; usuário `deploy` com chave restrita por `command=` ao `deploy.sh`; login no GHCR com `GITHUB_TOKEN` efêmero; `concurrency: production`; permissões mínimas por job.
- **Dependabot** mensal, agrupado (actions, uv, npm, docker).

## Consequências

- A `main` é o que está em produção; um deploy com falha fica visível (job vermelho) e é revertido manualmente com um comando.
- Migrações compatíveis com a versão anterior são **diretriz**, não regra. Depois de uma migração destrutiva, o rollback exige `alembic downgrade` antes de reimplantar a tag anterior.
- Rollback automático pode ser reavaliado quando houver dados ou uso que o justifiquem.
- Uma chave de deploy vazada só consegue executar o `deploy.sh`.
