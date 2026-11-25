# Plano de Entregas — Vocabulary Builder

> Detalha a Fase 0 e a Fase 1 (MVP) do roadmap (`project-overview.md`, seção 14) em entregas incrementais.
> Cada entrega é uma **fatia vertical** (banco → API → interface), **utilizável sozinha** e **termina em deploy de produção**.
> Questões em aberto referenciadas como `qN` correspondem à seção 15 do overview.

## Decisões deste plano

- **Deploy desde a E0.** A primeira entrega já vai para um ambiente público com HTTPS e autenticação. Consequência: hospedagem (q3) e autenticação (q2) passam a ser decisões de scaffolding.
- **Hospedagem (q3, resolvida):** VPS (Hostinger KVM 2, Brasil) com Docker Compose e Caddy; frontend e API na mesma origem; Postgres em container no VPS com backup diário criptografado em storage externo (implementado na E1, quando passam a existir dados reais). Ver [ADR 0001](adr/0001-hosting-vps-compose-caddy.md) e [ADR 0002](adr/0002-postgres-on-vps-with-offsite-backup.md).
- **Autenticação (q2, resolvida):** e-mail + senha com sessão server-side em cookie `HttpOnly`. Ver [ADR 0003](adr/0003-auth-password-server-side-sessions.md).
- **Scaffolding completo:** [`scaffolding-specification.md`](scaffolding-specification.md).
- **Infraestrutura entra só quando necessária:** backup externo na E1, Redis/fila na E2, object storage na E4.
- **Ordem:** captura → enriquecimento → revisão (a IA vem antes da revisão).

## Visão geral

| Entrega | Valor para o usuário | Infraestrutura nova | Decisões necessárias |
|---|---|---|---|
| E0 | (nenhum, só risco reduzido) | Deploy, CI/CD, autenticação, Postgres | q2, q3 (resolvidas) |
| E1 | Para de perder palavras | Backup externo | — |
| E2 | Termos explicados automaticamente | Fila, worker, LLM | q4, q5 |
| E3 | Hábito diário de revisão | FSRS | q10 |
| E4 | Ouvir e praticar | Object storage, TTS | provedor TTS, q7, q9 |
| E5 | Ponto de partida sem lista própria | Listas de frequência | q14, q8 |

Ao final da E5, o **critério de pronto do MVP** (seção 14) é atingido.

---

## E0 — Esqueleto no ar (walking skeleton)

**Status:** ✅ concluída (registro na S5 do [`scaffolding-blueprint.md`](scaffolding-blueprint.md#74-registro-de-sessões)).

**Objetivo:** aplicação vazia rodando em produção, com todo o caminho do código até o deploy funcionando.

**Escopo:**
- Monorepo `backend/` + `frontend/`.
- Backend FastAPI com estrutura em camadas (seção 8.2), `GET /health`, configuração via `.env`, logs estruturados, Alembic com a migração inicial (`users`, `sessions`).
- Frontend Vite + React + TS, roteamento, layout base, PWA mínima instalável, client gerado do OpenAPI, tela que consome `/health`.
- Autenticação simples (login/logout + rota protegida): e-mail + senha, sessão server-side em cookie.
- Qualidade: Ruff, mypy, pytest, ESLint, Prettier, Vitest, com um teste de exemplo em cada lado.
- `compose.yaml` local apenas com Postgres.
- CI (lint + testes a cada push) e CD (deploy automático na `main` com smoke test; rollback manual com um comando).
- Produção com HTTPS (VPS + Caddy), Postgres em container e segredos fora do repositório.
- Detalhes: [`scaffolding-specification.md`](scaffolding-specification.md).

**Fora do escopo:** qualquer `F-xx`, fila, worker, storage de arquivos, backup externo (E1), rollback automático.

**Decisões necessárias:** q2 (autenticação) e q3 (hospedagem), ambas resolvidas no `scaffolding-brainstorm` (ADRs 0001–0003).

**Pronto quando:** a URL pública abre no celular, a PWA instala, o login funciona e o status do backend aparece; um merge na `main` publica automaticamente e um deploy com falha pode ser revertido com `just deploy-rollback <sha>`.

---

## E1 — Captura e lista de termos

**Objetivo:** substituir as anotações manuais, guardando termos com contexto mesmo sem IA.

**Escopo:**
- F-01: captura individual (`term`, `context_sentence`, `source_url`, `source_timestamp`, `notes`).
- F-01: importação em lote (um termo por linha, formato opcional `termo | frase`).
- F-01: deduplicação por `normalized_text`; termo existente recebe nova `Occurrence`.
- F-13 básico: lista com busca e ordenação; detalhe com ocorrências; edição e exclusão.
- Modelo: `Term`, `Occurrence` (e opcionalmente `Tag`). Termos nascem com `status = pending`.
- Infra: backup diário criptografado em storage externo (`deploy/backup.sh`, systemd timer, `age` + `rclone`, ping de monitoramento), conforme spec §11.7 e ADR 0002.

**Fora do escopo:** enriquecimento, cartões, filtros por estado/CEFR.

**Decisões necessárias:** nenhuma bloqueante.

**Pronto quando:** o backup diário chega ao storage externo e um restore de teste funciona (**antes** de importar a lista real); a lista atual do usuário é importada sem duplicatas; capturar um termo pelo celular leva poucos segundos.

---

## E2 — Enriquecimento por IA

**Objetivo:** cada termo ganha automaticamente significado no contexto, IPA, registro, colocações, confusões comuns e frases de exemplo.

**Escopo:**
- F-02: enriquecimento assíncrono com saída estruturada validada por Pydantic (schema da seção 11.2); retry, status `failed`, reprocessamento manual.
- F-03: 3 a 5 frases de exemplo por termo.
- Fila + worker; port `LLMProvider` com adapter real e fake; prompts versionados em arquivo; `ProviderCallLog`.
- Interface: status "processando…" na lista; enriquecimento no detalhe; edição manual dos campos.
- Modelo: `TermEnrichment`, `ExampleSentence`, `Job` (se a fila não rastrear jobs), `ProviderCallLog`.
- Limite diário de chamadas de IA.

**Fora do escopo:** TTS, imagens, ajuste ao nível via modelo do aprendiz (nível fixo em configurações até a E5).

**Decisões necessárias:** q4 (fila), q5 (provedor/modelo de LLM).

**Pronto quando:** os termos da E1 ficam enriquecidos sem espera na tela e o custo por termo é visível no log.

---

## E3 — Revisão com repetição espaçada

**Objetivo:** fechar o ciclo principal e criar o hábito diário de revisão.

**Escopo:**
- F-06: FSRS (lib oficial `fsrs` atrás do port `Scheduler`) com cartão de **significado**, criado ao concluir o enriquecimento. Sessão diária: vencidos primeiro, limites de novos e revisões, notas Again/Hard/Good/Easy.
- F-07: classificação `new` / `learning` / `review` / `mastered` / `leech`; filtro por estado na lista.
- F-08: exercício de **reconhecimento**.
- Modelo: `Card`, `ReviewLog` (com snapshots antes/depois).
- Configurações: retenção desejada, limites diários.
- Testes determinísticos com relógio injetável.

**Fora do escopo:** cloze, áudio, cartão de pronúncia, painel de estatísticas.

**Decisões necessárias:** q10 (limiares de `mastered`/`leech`). Padrão configurável: 60 dias e 5 lapsos.

**Pronto quando:** uma sessão de cerca de 10 minutos no celular roda sem esperas perceptíveis e no dia seguinte aparecem os cartões corretos.

---

## E4 — Áudio, lacuna e exportação

**Objetivo:** enriquecer a revisão com áudio e exercícios objetivos e garantir a portabilidade dos dados.

**Escopo:**
- F-11: TTS do termo e das frases, gerado no worker, armazenado e reaproveitado; pré-carregamento do áudio do próximo cartão.
- Object storage (MinIO local, S3 compatível em produção); ports `ObjectStorage` (URLs assinadas) e `TTSProvider`.
- F-08: **cloze** com frase gerada sob demanda, correção automática tolerante a flexões e nota automática (seção 10.4).
- Regra de progressão de exercício por estabilidade do cartão.
- F-14: exportação completa em JSON.
- Modelo: `MediaAsset`.

**Fora do escopo:** gravação de voz (Fase 2), imagens, exportação Anki.

**Decisões necessárias:** provedor de TTS, q7 (sotaque; padrão americano), q9 (limiar de progressão; valor inicial simples e calibrável).

**Pronto quando:** os cartões tocam áudio sem atraso, o cloze aparece para cartões mais estáveis e o JSON com todos os dados pode ser baixado.

---

## E5 — Descoberta de palavras e modelo do aprendiz

**Objetivo:** resolver o cold start e criar a representação única do que o usuário sabe.

**Escopo:**
- F-19 inicial: `LearnerProfile` (faixa de frequência), `KnownWord`, `KnowledgeEvent`.
- F-16: importação de ao menos uma lista de frequência com licença verificada (ex.: NGSL) em `WordList` / `WordListEntry`.
- F-16: fluxo "Descobrir palavras" — lotes de 10 com "Já sei" / "Adicionar" / "Pular"; "Adicionar" cria `Term` com origem `frequency_list` e enfileira enriquecimento; faixa avança ou recua conforme as respostas; nunca sugere termos existentes ou conhecidos.
- Cartões `mastered` registram o lema como conhecido.
- Enriquecimento e frases passam a usar o nível do perfil.

**Fora do escopo:** teste de nivelamento e pacotes temáticos (Fase 3).

**Decisões necessárias:** q14 (listas de frequência e licenças), q8 (nível; começar autodeclarado).

**Pronto quando:** sem lista própria, o usuário gera termos pelo app, estuda esses termos e não vê de novo o que marcou como conhecido.

---

## Depois do MVP

As Fases 2 a 5 do overview (pronúncia, diário, imagens, estúdio de vídeo, conveniência) serão divididas da mesma forma quando chegar a hora.

## Fluxo de trabalho por entrega

- **E0:** `scaffolding-brainstorm` → `scaffolding-blueprint` → `scaffolding-development` → `scaffolding-review`.
- **Entregas com regra de negócio relevante** (E2, E3, E5 e as fases seguintes): fluxo completo `feature-spec-brainstorm` → `feature-blueprint` → `feature-development` → `feature-review`.
- **Entregas simples, de CRUD** (ex.: E1): **trilha leve**, com um FRD curto (escopo, regras, critérios de aceite) e implementação direta, sem blueprint nem relatórios intermediários. O `feature-review` é opcional. Em caso de dúvida sobre qual trilha usar, perguntar ao usuário.
