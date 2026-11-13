# 0009 — Client da API gerado com openapi-typescript e openapi-fetch

- **Status:** Aceita
- **Data:** 2026-11-12

## Contexto

O FastAPI gera o OpenAPI automaticamente; mudanças de contrato no backend devem quebrar a compilação do frontend, não a produção. Opções: openapi-typescript + openapi-fetch, Orval, Hey API; geração versionada ou no build.

## Decisão

- **openapi-typescript** (gera apenas tipos) + **openapi-fetch** (client tipado por caminho) + **openapi-react-query** (hooks tipados). Hooks finos por feature escritos à mão. Mocks com **openapi-msw**.
- `just gen-client` exporta `app.openapi()` sem subir servidor para um arquivo temporário e gera `frontend/src/api/schema.d.ts`, **o único arquivo versionado** (o JSON intermediário seria redundante para a checagem de drift).
- Componentes usam o `$api` diretamente; hooks próprios só quando há lógica além da chamada ou reuso.
- O CI regenera e falha se houver diferença (drift).
- FastAPI com `generate_unique_id_function` para operationIds estáveis.

## Consequências

- Código gerado mínimo e legível; o build do frontend não depende do Python.
- Mudanças de contrato aparecem no diff do PR (via `schema.d.ts`).
- Esquecer de rodar `just gen-client` é detectado pelo CI.
