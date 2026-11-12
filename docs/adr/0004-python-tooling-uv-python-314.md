# 0004 — Ferramentas Python: uv e Python 3.14

- **Status:** Aceita
- **Data:** 2026-11-12

## Contexto

O backend acumulará dependências pesadas (spaCy, SDKs de IA, SQLAlchemy). É preciso lockfile reprodutível, instalação rápida no CI e no Docker, e a mesma versão de Python em todos os ambientes. Candidatos: uv e Poetry. Versões: 3.13, 3.14 e 3.15 (lançada em 2026-10-09).

## Decisão

- **uv**: `pyproject.toml` no padrão PEP 621, `uv.lock` versionado, `.python-version`; versão do uv fixada no CI (`astral-sh/setup-uv`) e no Dockerfile.
- **Python 3.14**.

## Consequências

- Instalações muito mais rápidas no CI e no build de imagens; o uv também instala o Python (sem pyenv).
- O 3.15 fica para depois: o spaCy 3.8.x declara `Python < 3.15`. Subir de versão será trocar `.python-version`, `requires-python` e a imagem base.
- O uv evolui rápido; fixar a versão evita quebras.
