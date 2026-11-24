#!/usr/bin/env bash
# Deploy de uma versão no VPS. Executado pelo deploy.yml via SSH (usuário `deploy`):
#   echo "$GITHUB_TOKEN" | ssh deploy@host /opt/vocab/deploy/deploy.sh <sha> <ghcr_user>
# O token do GHCR chega pelo stdin (nunca como argumento, que apareceria no `ps`).
# Também serve para rollback manual: reimplanta a tag <sha> já publicada no GHCR.
set -euo pipefail

readonly APP_DIR=/opt/vocab
readonly ENV_FILE="$APP_DIR/.env"
readonly REGISTRY=ghcr.io
readonly REPOS=(ghcr.io/sgabriel-santos/vocab-api ghcr.io/sgabriel-santos/vocab-web)
readonly SMOKE_ATTEMPTS=10
readonly SMOKE_INTERVAL=6

usage() {
  echo "uso: echo <token> | $0 <sha de 40 caracteres> <usuário do GHCR>" >&2
  exit 2
}

[[ $# -eq 2 ]] || usage
sha="$1"
ghcr_user="$2"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo "SHA inválido: $sha" >&2; usage; }
[[ -n "$ghcr_user" ]] || usage

cd "$APP_DIR/deploy"

# Lê APP_DOMAIN do .env (sem `source`: o .env não é um script)
app_domain="$(grep -E '^APP_DOMAIN=' "$ENV_FILE" | tail -n1 | cut -d= -f2- | sed -E 's/[[:space:]]+#.*$//; s/^["'\'']//; s/["'\'']$//')"
[[ -n "$app_domain" ]] || { echo "APP_DOMAIN não definido em $ENV_FILE" >&2; exit 1; }

# Credencial do GHCR só durante o deploy
trap 'docker logout "$REGISTRY" >/dev/null 2>&1 || true' EXIT
read -r token
docker login "$REGISTRY" -u "$ghcr_user" --password-stdin <<<"$token" >/dev/null
unset token

export IMAGE_TAG="$sha"
compose=(docker compose --env-file "$ENV_FILE" -f compose.prod.yaml)

echo "==> pull $IMAGE_TAG"
"${compose[@]}" pull

echo "==> up (migrate roda antes da api pelo depends_on)"
"${compose[@]}" up -d --remove-orphans

echo "==> smoke test https://$app_domain/api/v1/health"
for attempt in $(seq 1 "$SMOKE_ATTEMPTS"); do
  if curl -fsS --max-time 5 "https://$app_domain/api/v1/health"; then
    echo
    echo "$sha" >"$APP_DIR/current_tag"
    # Mantém as duas tags mais recentes de cada imagem (a atual e a anterior, para rollback)
    for repo in "${REPOS[@]}"; do
      docker image ls "$repo" --format '{{.CreatedAt}}\t{{.Repository}}:{{.Tag}}' \
        | sort -r | tail -n +3 | cut -f2 \
        | xargs -r docker image rm >/dev/null 2>&1 || true
    done
    echo "==> deploy de $sha concluído"
    exit 0
  fi
  echo "tentativa $attempt/$SMOKE_ATTEMPTS falhou; nova tentativa em ${SMOKE_INTERVAL}s"
  sleep "$SMOKE_INTERVAL"
done

echo "==> SMOKE TEST FALHOU: $sha não respondeu em /api/v1/health." >&2
echo "    current_tag não foi alterado. Veja: docker compose -f compose.prod.yaml logs api migrate" >&2
exit 1
