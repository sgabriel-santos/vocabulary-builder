from app.adapters.security.argon2_hasher import Argon2PasswordHasher

hasher = Argon2PasswordHasher()


def test_hash_is_argon2id_and_verifies() -> None:
    password_hash = hasher.hash("correct-password")

    assert password_hash.startswith("$argon2id$")
    assert hasher.verify(password_hash, "correct-password")
    assert not hasher.verify(password_hash, "wrong-password")
    assert not hasher.needs_rehash(password_hash)


def test_verify_returns_false_for_invalid_hash() -> None:
    assert not hasher.verify("not-a-hash", "whatever")
