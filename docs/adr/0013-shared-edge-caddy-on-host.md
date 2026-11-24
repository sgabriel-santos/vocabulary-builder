# 0013 — Caddy de borda compartilhado no host da VPS

- **Status:** Aceita
- **Data:** 2026-11-23
- **Substitui:** o item "Caddy dentro do compose do projeto" do [ADR 0001](0001-hosting-vps-compose-caddy.md)

## Contexto

O ADR 0001 colocava o Caddy dentro do compose do projeto, como único serviço com portas publicadas (80/443) e responsável pelo HTTPS. Ele já previa a exceção: "se outro projeto passar a usar o mesmo VPS, o Caddy deve ser extraído para um edge compartilhado".

Isso aconteceu. A VPS (Ubuntu 26.04 LTS) já hospeda as stacks do GBS Ops Flow, e um **Caddy instalado no host** (pacote apt, serviço systemd) ocupa as portas 80/443. Ele emite os certificados Let's Encrypt de cada domínio e repassa para a porta em loopback de cada aplicação. Esse padrão está documentado no guia da VPS. O `web` do Vocabulary Builder, publicando 80/443, não subiria.

Alternativas avaliadas:

- **Caddy do host servindo a SPA e repassando `/api` direto para a `api`:** exigiria copiar o build do frontend para o host a cada deploy. Também levaria regras de cache e headers para o `/etc/caddy/Caddyfile`, que fica fora do git, e o rollback deixaria de ser só a troca da tag da imagem (contraria o ADR 0010).
- **Borda compartilhada num Caddy em container:** mexeria na produção do GBS sem ganho para nenhuma das aplicações.
- **VPS exclusiva:** mantém o desenho original, mas com custo recorrente extra.

## Decisão

- O **Caddy do host** termina o TLS de `vocab.gbs-software.com.br` (Let's Encrypt) e faz o redirect HTTP → HTTPS. Seu bloco é mínimo e configurado uma única vez, à mão:
  ```caddy
  vocab.gbs-software.com.br {
  	reverse_proxy 127.0.0.1:9001
  }
  ```
- A imagem `web` continua com Caddy, servindo a SPA e fazendo proxy de `/api/*` para a `api`. Ela atende **só HTTP em `:80`** (`auto_https off`), publicada em **`127.0.0.1:9001`**, a porta da faixa 9001+ reservada pelo guia da VPS para aplicações que não são do GBS.
- O Caddy da imagem confia nos `X-Forwarded-*` vindos de faixas privadas (`trusted_proxies static private_ranges`), por onde chega o tráfego do Caddy do host via rede do Docker. O Caddy do host não confia em ninguém, então reescreve o `X-Forwarded-For` com o IP real do cliente. A `api` lê esse IP com `--proxy-headers`.
- Headers de segurança (HSTS etc.), cache e fallback da SPA continuam no `frontend/Caddyfile`, versionados.
- O compose de produção tem nome fixo (`name: vocab`): containers, rede e volumes com prefixo único na VPS compartilhada.
- Frontend e API continuam na **mesma origem**: nada muda em cookie, CORS ou checagem de `Origin` (ADR 0003).

## Consequências

- HTTPS, deploy automático e rollback continuam como antes (ADR 0011): o deploy só troca os containers atrás da `127.0.0.1:9001` e nunca toca o Caddy do host. O smoke test em `https://<APP_DOMAIN>/api/v1/health` passa pelo Caddy do host, então valida o caminho completo.
- Um hop extra de proxy, local à máquina (custo desprezível).
- O Vocabulary Builder passa a depender do Caddy do host: um reload com erro ou uma parada dele derruba também esta aplicação. Mudanças no `/etc/caddy/Caddyfile` são feitas como root, fora do CI, seguindo o guia da VPS.
- Somem os volumes `caddy_data`/`caddy_config`, já que os certificados ficam com o Caddy do host.
- Hardening do host (firewall, SSH) e versão do sistema são da VPS compartilhada, não deste projeto. Ficam fora do runbook do vocab.
- Toda mudança deste projeto na VPS (porta, domínio, diretório) deve ser registrada também no guia da VPS.
