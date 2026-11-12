# 0005 — Ferramentas do frontend: pnpm e Node 26 LTS

- **Status:** Aceita
- **Data:** 2026-11-12

## Contexto

O Node é usado apenas para desenvolvimento, testes e build do SPA; não roda em produção (o Caddy serve arquivos estáticos). Candidatos: npm, pnpm e Bun; Node 24 (Maintenance LTS) e Node 26 (Active LTS desde o fim de outubro de 2026).

## Decisão

- **pnpm**, com versão fixada no campo `packageManager` do `package.json`; `pnpm-lock.yaml` versionado.
- **Node 26 LTS**, fixado em `.nvmrc` e `engines`.
- Sem gerenciador de versões multi-linguagem (mise/asdf): o uv cuida do Python, `.nvmrc` do Node.

## Consequências

- Instalação rápida e estrita (sem dependências fantasmas).
- O Corepack não acompanha mais o Node: o pnpm é instalado standalone localmente e via `pnpm/action-setup` no CI.
- Node 26 tem suporte até ~abril de 2029.
