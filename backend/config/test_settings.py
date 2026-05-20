"""Configurações específicas para execução da suíte de testes.

Mantém o restante das opções do projeto e troca apenas o banco por SQLite
em memória, evitando dependência de um PostgreSQL ativo para validar a base.
"""

from .settings import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
