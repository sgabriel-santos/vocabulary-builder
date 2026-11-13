# Imagem `api`: usada pela API, pelo `migrate` (alembic) e pela CLI administrativa.
# Segredos nunca entram na imagem: chegam por env_file e /run/secrets em runtime.

FROM python:3.14.10-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
# Dependências primeiro: a camada só é refeita quando o lock muda
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini ./

FROM python:3.14.10-slim
LABEL org.opencontainers.image.source="https://github.com/sgabriel-santos/vocabulary-builder"
RUN useradd --uid 1000 --create-home app
WORKDIR /app
COPY --from=builder --chown=app:app /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4)"]
# --forwarded-allow-ips "*": a api não publica portas; só o Caddy a alcança pela rede interna
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
