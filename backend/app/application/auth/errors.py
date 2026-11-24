"""Exceções dos casos de uso de autenticação."""


class InvalidCredentials(Exception):
    """E-mail inexistente ou senha incorreta (indistinguíveis de propósito)."""


class UserAlreadyExists(Exception):
    pass


class InvalidUserInput(ValueError):
    """E-mail ou senha fora das regras mínimas de cadastro."""
