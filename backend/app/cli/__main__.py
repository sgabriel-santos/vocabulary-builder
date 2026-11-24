"""CLI administrativa: `python -m app.cli <comando>`.

- create-user <email>: cria um usuário (senha via prompt, nunca por argumento).
- seed-dev: cria o usuário de desenvolvimento (idempotente; recusado em produção).
"""

import argparse
import asyncio
import getpass
import sys

from app.adapters.db.engine import build_engine, build_sessionmaker
from app.adapters.security.argon2_hasher import Argon2PasswordHasher
from app.application.auth.create_user import create_user
from app.application.auth.errors import InvalidUserInput, UserAlreadyExists
from app.core.config import Settings, get_settings


async def _create_user(settings: Settings, email: str, password: str) -> None:
    engine = build_engine(settings)
    try:
        async with build_sessionmaker(engine)() as db:
            await create_user(db, Argon2PasswordHasher(), email=email, password=password)
    finally:
        await engine.dispose()


def cmd_create_user(settings: Settings, email: str) -> int:
    password = getpass.getpass("Senha: ")
    if getpass.getpass("Confirme a senha: ") != password:
        print("As senhas não conferem.", file=sys.stderr)
        return 1
    try:
        asyncio.run(_create_user(settings, email, password))
    except InvalidUserInput as exc:
        print(f"Dados inválidos: {exc}", file=sys.stderr)
        return 1
    except UserAlreadyExists:
        print(f"Já existe um usuário com o e-mail {email}.", file=sys.stderr)
        return 1
    print(f"Usuário criado: {email}")
    return 0


def cmd_seed_dev(settings: Settings) -> int:
    if settings.app_env == "production":
        print("seed-dev não pode rodar em produção.", file=sys.stderr)
        return 1
    email = settings.seed_user_email
    try:
        asyncio.run(_create_user(settings, email, settings.seed_user_password.get_secret_value()))
    except UserAlreadyExists:
        print(f"Usuário de desenvolvimento já existe: {email}")
        return 0
    except InvalidUserInput as exc:
        print(f"SEED_USER_* inválido: {exc}", file=sys.stderr)
        return 1
    print(f"Usuário de desenvolvimento criado: {email}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user", help="cria um usuário (senha via prompt)")
    create.add_argument("email")
    sub.add_parser("seed-dev", help="cria o usuário de desenvolvimento")
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.command == "create-user":
        return cmd_create_user(settings, args.email)
    return cmd_seed_dev(settings)


if __name__ == "__main__":
    sys.exit(main())
