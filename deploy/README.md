# Runbook de produção

Tudo que o Vocabulary Builder roda na VPS. A VPS é **compartilhada** com as stacks do GBS Ops Flow (Ubuntu 26.04, operada como `root`). Sistema, Docker, Caddy do host, firewall, SSH e convenções de porta são descritos no **guia da VPS** (`GUIA-VPS.md`, fora deste repositório). Este runbook cobre só o que é do vocab, seguindo a receita "Outra aplicação" do guia.

Decisões: [ADR 0001](../docs/adr/0001-hosting-vps-compose-caddy.md) (VPS + Compose), [0013](../docs/adr/0013-shared-edge-caddy-on-host.md) (Caddy de borda no host), [0002](../docs/adr/0002-postgres-on-vps-with-offsite-backup.md) (Postgres e backup), [0010](../docs/adr/0010-docker-images-and-compose-layout.md) (imagens e compose), [0011](../docs/adr/0011-ci-cd-auto-deploy-with-rollback.md) (deploy e rollback).

```
Internet ──HTTPS──▶ Caddy do host (systemd, :80 :443, Let's Encrypt; compartilhado)
                     └── vocab.gbs-software.com.br ─▶ 127.0.0.1:9001
                                                       │
Projeto compose `vocab`:                               ▼
                    web (Caddy + SPA, só HTTP :80)   ← único serviço com porta, só em loopback
                     ├── /api/*  → api:8000
                     └── /*      → SPA (fallback index.html)
                    api ──▶ db (postgres:18, volume vocab_db_data)
                    migrate (one-off: alembic upgrade head, antes da api)
```

| Item | Valor |
|---|---|
| Domínio | `vocab.gbs-software.com.br` |
| Porta no host | `127.0.0.1:9001` (faixa 9001+ do guia da VPS) |
| Diretório | `/opt/vocab` (fora de `/opt/gbs`, que é varrido pelo backup do GBS) |
| Projeto compose | `vocab` (containers `vocab-<serviço>-1`, rede `vocab_default`, volume `vocab_db_data`) |

## Layout no VPS

```
/opt/vocab/                          # dono: deploy
├── .env                             # configuração de produção (chmod 600, não versionado)
├── current_tag                      # SHA em produção (gravado pelo deploy.sh após o smoke test)
└── deploy/                          # copiado do repositório a cada deploy (rsync --delete, exceto secrets/)
    ├── compose.prod.yaml
    ├── deploy.sh
    ├── README.md
    └── secrets/                     # chmod 700, dono deploy; criado à mão, nunca sobrescrito pelo deploy
        └── postgres_password        # chmod 444 (ver "Segredos")
```

## 1. Setup inicial na VPS (uma vez)

Execute como `root` na VPS (`ssh root@<ip da VPS>`). Docker, Compose, Caddy do host e atualizações automáticas já existem (guia da VPS). Hardening do host (firewall, SSH) é pendência do guia da VPS, fora deste runbook.

### 1.1 Pré-checagem

```bash
ss -tlnp | grep :9001 || echo "9001 livre"   # porta reservada para o vocab
docker compose version
free -h && df -h /                            # o compose do vocab limita ~2,8 GB no total
apt-get install -y rsync curl                 # o CI usa rsync; o deploy.sh usa curl
```

### 1.2 Usuário `deploy`

O GitHub Actions entra na VPS como `deploy`, dono de `/opt/vocab`. Ele fica no grupo `docker` (o que equivale a root no host) e **sem sudo**.

```bash
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy
mkdir -p /opt/vocab/deploy/secrets
chown -R deploy:deploy /opt/vocab
chmod 700 /opt/vocab/deploy/secrets
```

> O grupo `docker` dá ao `deploy` controle sobre **todos** os containers da VPS, inclusive os do GBS. A chave dele é exclusiva do CI e fica só no Environment `production` do GitHub.

Gere, **na sua máquina**, um par de chaves exclusivo do deploy (sem passphrase, já que o CI o usa):

```bash
ssh-keygen -t ed25519 -C vocab-deploy -f ~/.ssh/vocab-deploy -N ""
```

No VPS, coloque a chave **pública** em `~deploy/.ssh/authorized_keys` com restrições (sem `command=`: o CI precisa rodar `rsync` e o `deploy.sh`):

```bash
sudo -u deploy mkdir -p -m 700 /home/deploy/.ssh
echo 'no-port-forwarding,no-agent-forwarding,no-X11-forwarding ssh-ed25519 AAAA... vocab-deploy' \
  | sudo -u deploy tee /home/deploy/.ssh/authorized_keys
chmod 600 /home/deploy/.ssh/authorized_keys
```

A chave **privada** vai só para o secret `DEPLOY_SSH_KEY` do Environment `production` (seção 2). Para revogar o acesso do CI, basta remover essa linha do `authorized_keys`.

### 1.3 Configuração e segredos

`/opt/vocab/.env` (dono `deploy`, `chmod 600`; crie com `sudo -u deploy sh -c 'umask 077; cat > /opt/vocab/.env'` e cole o conteúdo):

```dotenv
APP_ENV=production
APP_DOMAIN=vocab.gbs-software.com.br
LOG_LEVEL=INFO
LOG_FORMAT=json
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=vocab
POSTGRES_USER=vocab
SESSION_COOKIE_SECURE=true
SESSION_TTL_DAYS=60
LOGIN_RATE_LIMIT=5/minute
```

> **Não** coloque `POSTGRES_PASSWORD` no `.env`: variável de ambiente tem precedência sobre `/run/secrets` no pydantic-settings. A senha vem só do arquivo de secret.

Senha do Postgres:

```bash
sudo -u deploy sh -c 'umask 077; openssl rand -base64 32 | tr -d "\n" > /opt/vocab/deploy/secrets/postgres_password'
chmod 444 /opt/vocab/deploy/secrets/postgres_password
```

**Por que 444 e não 600:** sem Swarm, o Compose monta o arquivo de secret por bind mount, preservando dono e modo do host. O processo da `api` roda como `app` (uid 1000) dentro do container. Com `600`, ele só conseguiria ler o arquivo se o `deploy` também tivesse uid 1000. A proteção fica no diretório `secrets/` (`700`, dono `deploy`): nenhum outro usuário do host chega ao arquivo. A senha só é usada pelo Postgres na **primeira** inicialização do volume `db_data`; trocá-la depois exige `ALTER USER` no banco.

### 1.4 DNS (Registro.br)

Na zona `gbs-software.com.br`: registro `A` `vocab` → IP da VPS. Confira antes de seguir: `dig +short vocab.gbs-software.com.br`. O Caddy do host só consegue emitir o certificado quando o domínio já aponta para a VPS.

### 1.5 Caddy do host

Acrescente ao `/etc/caddy/Caddyfile` (sem o snippet `gbs_cliente`, que é do GBS):

```caddy
vocab.gbs-software.com.br {
	reverse_proxy 127.0.0.1:9001
}
```

```bash
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile && systemctl reload caddy
```

Se a config for inválida, o reload falha e a anterior continua no ar (o GBS não cai). Até o primeiro deploy, `https://vocab.gbs-software.com.br` responde `502`, porque ainda não há nada na `9001`. O certificado é emitido mesmo assim (`journalctl -u caddy --since "5 min ago"`).

HTTPS, redirect HTTP → HTTPS e HTTP/3 são do Caddy do host. Headers de segurança, cache e fallback da SPA ficam no `frontend/Caddyfile` (versionado, dentro da imagem `web`).

### 1.6 Registrar no guia da VPS

O guia da VPS manda registrar toda aplicação nova. Atualize as seções 3 (`/opt/vocab`), 4 (stack `vocab`), 6 (porta 9001, registro DNS, bloco do Caddy) e o histórico. Atualize também a cópia de referência do Caddyfile do host.

## 2. GitHub (uma vez)

1. **Settings → Environments → `production`**, com *deployment branch rule* permitindo só a `main`.
2. Secrets do Environment:

   | Secret | Valor |
   |---|---|
   | `DEPLOY_HOST` | IP ou hostname do VPS |
   | `DEPLOY_SSH_KEY` | conteúdo de `~/.ssh/vocab-deploy` (chave privada) |
   | `DEPLOY_KNOWN_HOSTS` | saída de `ssh-keyscan -t ed25519 <host>`, **conferida** contra a fingerprint vista no console do VPS (`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`) |

3. Variáveis do Environment: `APP_DOMAIN` = `vocab.gbs-software.com.br` e `DEPLOY_USER` = `deploy`. O `DEPLOY_USER` é variável, não secret: o GitHub mascara nos logs todo texto igual ao valor de um secret, e "deploy" apareceria como `***`.
4. Depois do primeiro push de imagens, conferir em **Packages** que `vocab-api` e `vocab-web` estão ligados ao repositório (o `LABEL org.opencontainers.image.source` das imagens faz isso). Sem a ligação, o `GITHUB_TOKEN` do deploy não consegue fazer `pull`.

## 3. Deploy

Automático a cada merge na `main` (`.github/workflows/deploy.yml`): CI → build e push de `vocab-api:<sha>` e `vocab-web:<sha>` no GHCR → `rsync` de `deploy/` → `deploy.sh <sha>` via SSH.

O `deploy.sh`:

1. Valida o SHA (`^[0-9a-f]{40}$`) e faz `docker login ghcr.io` com o token recebido pelo stdin.
2. `docker compose pull` e `up -d --remove-orphans` com `IMAGE_TAG=<sha>`. O `migrate` roda antes da `api` (`depends_on`).
3. Smoke test: até 10 tentativas, a cada 6 s, de `https://$APP_DOMAIN/api/v1/health`.
4. Sucesso: grava `/opt/vocab/current_tag`, remove imagens antigas (mantém as duas tags mais recentes de cada imagem) e faz `docker logout`.
5. Falha: `docker logout`, mensagem de erro e `exit 1` (job vermelho). **Não há rollback automático** e `current_tag` não muda.

Todos os comandos abaixo rodam no VPS, como `deploy`, a partir de `/opt/vocab/deploy`. Para encurtar:

```bash
cd /opt/vocab/deploy
export IMAGE_TAG="$(cat /opt/vocab/current_tag)"
alias dc='docker compose --env-file /opt/vocab/.env -f compose.prod.yaml'
```

### Primeiro usuário

Não há cadastro público. Depois do primeiro deploy:

```bash
dc run --rm api python -m app.cli create-user <seu-email>   # senha via prompt (mínimo 8 caracteres)
```

### Operação do dia a dia

```bash
dc ps                       # estado dos serviços
dc logs -f --tail=100 api   # logs da api (JSON); também: web, db, migrate
curl -s http://127.0.0.1:9001/api/v1/health   # direto no web, sem o Caddy do host
dc exec db psql -U vocab vocab
```

Confira nos logs da `api` que o IP real do cliente aparece nas linhas de acesso. O rate limit de login depende disso. O Caddy do host monta o `X-Forwarded-For`, o Caddy do `web` o repassa (`trusted_proxies`) e a `api` o lê (`--proxy-headers`). Se aparecer sempre o mesmo IP interno do Docker, todos os clientes estão dividindo um único limite.

## 4. Rollback (manual)

Reimplanta uma tag já publicada no GHCR, sem rebuild:

- **GitHub:** Actions → *Deploy* → *Run workflow* → `sha` = SHA anterior (veja o histórico de deploys ou `current_tag` antes do deploy ruim); ou
- **Terminal:** `just deploy-rollback <sha>` (requer `gh` autenticado).

O `workflow_dispatch` faz checkout da `main` **atual**, então o `compose.prod.yaml` copiado é o da `main`, não o da época do `<sha>`. Se o compose mudou de forma incompatível nesse intervalo, reverta o compose num PR em vez de usar o rollback.

**Rollback depois de migração destrutiva:** o rollback não reverte schema. Antes de reimplantar a tag anterior, rode o `downgrade` com a imagem **nova**, a única que conhece a migração:

```bash
IMAGE_TAG=<sha com falha> dc run --rm migrate alembic downgrade <revisão anterior>
```

Depois, faça o rollback normal para a tag anterior.

## 5. Volumes (cuidado)

| Volume | Conteúdo | Perder significa |
|---|---|---|
| `vocab_db_data` | Banco de dados | Perda de dados (até a E1, só o usuário; depois, restaurar do backup) |

Os certificados ficam com o Caddy do host (`/var/lib/caddy/`), fora deste projeto.

Nunca rode `docker compose down -v` em produção.

## 6. Backup e restore

**Pendente (entra na E1).** Terá script e timer próprios, em `/opt/vocab` (o `backup-gbs.sh` do GBS só varre `/opt/gbs/*`), e entrará no registro do guia da VPS. Até lá, o banco só tem o usuário criado pela CLI, recriável em segundos. O desenho já está decidido (spec §11.7, ADR 0002): `backup.sh` diário via systemd timer → `pg_dump -Fc` → `age` → `rclone` para B2/R2 → ping no Healthchecks.io; restore com `age -d` + `pg_restore --clean --if-exists`, testado no setup.
