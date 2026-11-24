class FakePasswordHasher:
    """Hasher previsível e rápido: `hash(p) == "fake$" + p`."""

    PREFIX = "fake$"

    def hash(self, password: str) -> str:
        return self.PREFIX + password

    def verify(self, password_hash: str, password: str) -> bool:
        return password_hash == self.PREFIX + password

    def needs_rehash(self, password_hash: str) -> bool:
        return False
