# 0006 — Persistência: SQLAlchemy 2.0 async, psycopg 3 e separação domínio × ORM

- **Status:** Aceita
- **Data:** 2026-11-12

## Contexto

O domínio é rico (Term, Card, ReviewLog, LearnerProfile...), usa JSONB e terá consultas não triviais (montagem da sessão de revisão). A arquitetura é hexagonal "sem exagero de cerimônia" (overview §8.2), e as regras de domínio (FSRS, mastery/leech) devem ser testáveis sem banco. Opções avaliadas: SQLAlchemy 2.0, SQLModel, SQL sem ORM; drivers asyncpg e psycopg 3.

## Decisão

- **SQLAlchemy 2.0 async** com modelos tipados (`Mapped[...]`) em `app/adapters/db/models/`; Alembic para migrações.
- **psycopg 3** como driver único (async na aplicação, sync no Alembic, na CLI e em fixtures).
- **Separação com bom senso**: agregados com regra de negócio têm entidade de domínio (dataclass em `app/domain/`) e repositório (port em `app/ports/`, implementação em `app/adapters/db/repositories/`). Leituras simples (listagens, filtros) podem consultar o ORM diretamente na camada `application/` e devolver DTOs.

## Consequências

- Domínio testável sem banco; ORM com suporte completo a JSONB, constraints e consultas complexas.
- Custo de mapeamento ORM ↔ domínio nos agregados com regra.
- Agentes não devem expor modelos ORM na camada `api/` nem colocar regra de negócio em routers.
