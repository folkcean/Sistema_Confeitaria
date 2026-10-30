"""
app / config.py

Configuração do Flask, lida do .env
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Lê o .env da raiz do projeto (a pasta acima de app/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Config:
    """
    Configuração padrão. O app.config.from_object() copia os atributos em MAIÚSCULAS
    """

    # Assina o cookie da sessão; sem ela no .env o app nem sobe (KeyError)
    SECRET_KEY = os.environ["SECRET_KEY"]

    # Banco (os mesmos nomes do .env que o docker-compose usa)
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_USER = os.environ["POSTGRES_USER"]
    POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
    POSTGRES_DB = os.environ["POSTGRES_DB"]

    # Upload de fotos até 5 MB (acima disso o Flask responde 413)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    # Cookie da sessão não vai junto em POST vindo de outro site
    SESSION_COOKIE_SAMESITE = "Lax"

    # Duração da sessão com "Lembrar de mim" marcado
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)


class ConfigTeste(Config):
    """
    Configuração dos testes: herda tudo e liga o modo de teste do Flask
    """

    TESTING = True
