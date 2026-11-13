# Runbook de produção

Tudo que roda no VPS (Hostinger KVM 2, Ubuntu 24.04). Decisões: [ADR 0001](../docs/adr/0001-hosting-vps-compose-caddy.md) (VPS + Compose + Caddy), [0002](../docs/adr/0002-postgres-on-vps-with-offsite-backup.md) (Postgres e backup), [0010](../docs/adr/0010-docker-images-and-compose-layout.md) (imagens e compose), [0011](../docs/adr/0011-ci-cd-auto-deploy-with-rollback.md) (deploy e rollback).

```
Internet ──HTTPS──▶ web (Caddy + SPA) :80 :443 :443/udp   ← único serviço com portas
                     ├── /api/*  → api:8000
                     └── /*      → SPA (fallback index.html)
                    api ──▶ db (postgres:18, volume db_data)
                    migrate (one-off: alembic upgrade head, antes da api)
```

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

## 1. Setup inicial do VPS (uma vez)

Execute como o usuário administrativo (com sudo). Substitua `<domínio>` pelo domínio registrado.

### 1.1 Hardening

1. Criar um usuário administrativo com sudo e a sua chave SSH pessoal em `~/.ssh/authorized_keys`. Testar o login com ele **antes** do próximo passo.
2. Em `/etc/ssh/sshd_config` (ou num arquivo em `/etc/ssh/sshd_config.d/`): `PasswordAuthentication no` e `PermitRootLogin no`; `sudo systemctl restart ssh`.
3. Firewall (`ufw` ou o firewall do painel da Hostinger), liberando só 22, 80, 443/tcp e 443/udp:
   ```bash
   sudo ufw default deny incoming && sudo ufw default allow outgoing
   sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw allow 443/udp
   sudo ufw enable
   ```
   > O Docker publica portas direto no iptables, por fora do `ufw`. Por isso o `compose.prod.yaml` só publica portas no `web`.
4. Atualizações automáticas: `sudo apt-get install -y unattended-upgrades && sudo dpkg-reconfigure -plow unattended-upgrades`.

### 1.2 Docker

Instalar o Docker Engine e o plugin Compose pelo [repositório oficial](https://docs.docker.com/engine/install/ubuntu/) (não usar o pacote `docker.io` do Ubuntu). Conferir com `docker compose version`. Garantir `rsync` e `curl`: `sudo apt-get install -y rsync curl`.

### 1.3 Usuário `deploy`

O GitHub Actions entra no VPS como `deploy`. Ele fica no grupo `docker` (o que equivale a root no host) e **sem sudo**.

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy
sudo mkdir -p /opt/vocab/deploy/secrets
sudo chown -R deploy:deploy /opt/vocab
sudo chmod 700 /opt/vocab/deploy/secrets
```

Gere, **na sua máquina**, um par de chaves exclusivo do deploy (sem passphrase, já que o CI o usa):

```bash
ssh-keygen -t ed25519 -C vocab-deploy -f ~/.ssh/vocab-deploy -N ""
```

No VPS, coloque a chave **pública** em `~deploy/.ssh/authorized_keys` com restrições (sem `command=`: o CI precisa rodar `rsync` e o `deploy.sh`):

```bash
sudo -u deploy mkdir -p -m 700 /home/deploy/.ssh
echo 'no-port-forwarding,no-agent-forwarding,no-X11-forwarding ssh-ed25519 AAAA... vocab-deploy' \
  | sudo -u deploy tee /home/deploy/.ssh/authorized_keys
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

A chave **privada** vai só para o secret `DEPLOY_SSH_KEY` do Environment `production` (seção 2). Para revogar o acesso do CI, basta remover essa linha do `authorized_keys`.

### 1.4 Configuração e segredos

`/opt/vocab/.env` (dono `deploy`, `chmod 600`):

```dotenv
APP_ENV=production
APP_DOMAIN=vocab.<domínio>
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
sudo chmod 444 /opt/vocab/deploy/secrets/postgres_password
```

**Por que 444 e não 600:** sem Swarm, o Compose monta o arquivo de secret por bind mount, preservando dono e modo do host. O processo da `api` roda como `app` (uid 1000) dentro do container. Com `600`, ele só conseguiria ler o arquivo se o `deploy` também tivesse uid 1000. A proteção fica no diretório `secrets/` (`700`, dono `deploy`): nenhum outro usuário do host chega ao arquivo. A senha só é usada pelo Postgres na **primeira** inicialização do volume `db_data`; trocá-la depois exige `ALTER USER` no banco.

### 1.5 DNS (Registro.br)

Registro `A` `vocab` → IP do VPS (e `AAAA` se houver IPv6). Confira antes do primeiro deploy: `dig +short vocab.<domínio>`. O Caddy só consegue emitir o certificado quando o domínio já aponta para o VPS.

## 2. GitHub (uma vez)

1. **Settings → Environments → `production`**, com *deployment branch rule* permitindo só a `main`.
2. Secrets do Environment:

   | Secret | Valor |
   |---|---|
   | `DEPLOY_HOST` | IP ou hostname do VPS |
   | `DEPLOY_USER` | `deploy` |
   | `DEPLOY_SSH_KEY` | conteúdo de `~/.ssh/vocab-deploy` (chave privada) |
   | `DEPLOY_KNOWN_HOSTS` | saída de `ssh-keyscan -t ed25519 <host>`, **conferida** contra a fingerprint vista no console do VPS (`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`) |

3. Variável do Environment: `APP_DOMAIN` = `vocab.<domínio>`.
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
dc exec db psql -U vocab vocab
```

Confira nos logs da `api` que o IP real do cliente aparece nas linhas de acesso. O rate limit de login depende disso (`--proxy-headers`). Se aparecer sempre o mesmo IP interno do Docker, todos os clientes estão dividindo um único limite.

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
| `db_data` | Banco de dados | Perda de dados (até a E1, só o usuário; depois, restaurar do backup) |
| `caddy_data` / `caddy_config` | Certificados e estado do Caddy | Reemissão de certificados; repetir isso esbarra no rate limit do Let's Encrypt |

Nunca rode `docker compose down -v` em produção.

## 6. Backup e restore

**Pendente (entra na E1).** Até lá, o banco só tem o usuário criado pela CLI, recriável em segundos. O desenho já está decidido (spec §11.7, ADR 0002): `backup.sh` diário via systemd timer → `pg_dump -Fc` → `age` → `rclone` para B2/R2 → ping no Healthchecks.io; restore com `age -d` + `pg_restore --clean --if-exists`, testado no setup.
