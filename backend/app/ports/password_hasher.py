from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool:
        """True se a senha confere; False se não confere ou se o hash é inválido."""
        ...

    def needs_rehash(self, password_hash: str) -> bool:
        """True se o hash foi gerado com parâmetros diferentes dos atuais."""
        ...
