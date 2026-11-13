# 0008 — Roteamento do frontend com TanStack Router

- **Status:** Aceita
- **Data:** 2026-11-12

## Contexto

SPA sem SSR, com rota protegida desde a E0 e telas com estado na URL (lista de termos com busca, filtros e ordenação — F-13). O estado de servidor fica no TanStack Query. Opções: React Router v7 e TanStack Router.

## Decisão

**TanStack Router** com rotas por arquivo (`src/routes/`, árvore gerada em `src/routeTree.gen.ts` pelo plugin do Vite), search params tipados e validados, proteção de rotas via `beforeLoad` em um layout `_authenticated`, e loaders integrados ao TanStack Query.

## Consequências

- Links e parâmetros inválidos viram erro de compilação; filtros na URL são tipados.
- Pré-carregamento de dados via loaders ajuda o requisito de "sem esperas perceptíveis".
- Curva de aprendizado e dependência de um plugin de geração de código; o arquivo gerado é versionado e nunca editado à mão.
