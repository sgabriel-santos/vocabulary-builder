"""Imprime o schema OpenAPI da API em stdout (usado por `just gen-client`).

Não conecta no banco: o lifespan não roda ao gerar o schema.
"""

import json

from app.main import create_app


def main() -> None:
    print(json.dumps(create_app().openapi(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
