# 0012 — Branching com PR e squash merge

- **Status:** Aceita
- **Data:** 2026-11-12

## Contexto

Cada merge na `main` vai para produção (ADR 0011). Boa parte do código será produzida por agentes de IA seguindo o pipeline de skills, e o Dependabot também abre PRs. Opções: push direto na `main` (trunk-based), branches curtas com PR, Git Flow.

## Decisão

- Branches curtas a partir da `main` (`feat/F-01-...`, `fix/...`, `chore/...`, `docs/...`), integradas por **PR**.
- Ruleset na `main`: sem push direto, status checks do CI obrigatórios, histórico linear, sem force push; sem aprovação obrigatória (projeto solo).
- **Squash merge**, com o título do PR em Conventional Commits referenciando `F-xx`.

## Consequências

- `main` sempre verde e publicável; o PR é o ponto de revisão do diff consolidado (inclusive do código gerado por agentes).
- Histórico da `main` legível como changelog de entregas; commits granulares permanecem visíveis no PR.
- Alguns passos a mais por mudança.
