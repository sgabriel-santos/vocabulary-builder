# 0001 — Hospedagem em VPS com Docker Compose e Caddy

- **Status:** Aceita
- **Data:** 2026-11-12
- **Resolve:** questão em aberto q3 (overview §15)

## Contexto

O deploy em produção acontece desde a E0 (delivery plan). O host precisa acomodar, sem migração, o roadmap inteiro: API, worker sempre ligado (E2), Redis/fila, object storage (E4), ffmpeg e spaCy. Requisitos: HTTPS (microfone e PWA), revisão diária sem esperas perceptíveis (cold start é inaceitável), custo de poucos dólares por mês e portabilidade via containers. Foram avaliados PaaS (Railway/Render/Fly.io), serverless (Cloud Run + Neon) e VPS em vários provedores e regiões.

## Decisão

- **VPS Hostinger KVM 2** (2 vCPU / 8 GB / 100 GB NVMe), data center no Brasil, contrato de 24 meses. Ubuntu 24.04 LTS sem painel.
- **Docker Compose** orquestra todos os serviços.
- **Caddy dentro do compose do projeto**: único serviço com portas publicadas, HTTPS automático (Let's Encrypt), serve o build do SPA e faz proxy de `/api/*` para a API. Frontend e API na **mesma origem** (`vocab.<domínio>`).
- Domínio registrado no Registro.br, com o DNS do próprio Registro.br.

## Consequências

- Custo fixo e baixo, sem cold start, latência local (Brasil).
- Mesma origem: sem CORS e com cookie de sessão `SameSite` simples (ADR 0003).
- A operação do servidor (atualizações, firewall, backups) fica com o desenvolvedor; mitigada com `unattended-upgrades`, firewall mínimo e runbook em `deploy/README.md`.
- Pagamento antecipado (24 meses); lock-in técnico baixo, pois migrar é subir o Compose em outro host e restaurar o backup.
- Se outro projeto passar a usar o mesmo VPS, o Caddy deve ser extraído para um "edge" compartilhado.
