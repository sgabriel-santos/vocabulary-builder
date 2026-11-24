FROM node:26.13.1-slim AS build
# Mesma versão do "packageManager" do package.json
RUN npm install -g pnpm@12.18.0
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM caddy:2.11.9-alpine
LABEL org.opencontainers.image.source="https://github.com/sgabriel-santos/vocabulary-builder"
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 80
