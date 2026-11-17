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

    ABACATEPAY_API_KEY = os.getenv("ABACATEPAY_API_KEY", "")

    # E-mail (verificação do e-mail do cliente). Sem EMAIL_SMTP_HOST nada é enviado de verdade:
    # o e-mail aparece no terminal do Flask (modo desenvolvimento)
    EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "")
    EMAIL_SMTP_PORTA = os.getenv("EMAIL_SMTP_PORTA", "587")
    EMAIL_SMTP_USUARIO = os.getenv("EMAIL_SMTP_USUARIO", "")
    EMAIL_SMTP_SENHA = os.getenv("EMAIL_SMTP_SENHA", "")
    # "sim" liga o STARTTLS (criptografia). Servidor de teste local (Mailpit) usa "nao"
    EMAIL_SMTP_TLS = os.getenv("EMAIL_SMTP_TLS", "sim").strip().lower() == "sim"
    EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "Dolce Bea <noreply@localhost>")
    
class ConfigTeste(Config):
    """
    Configuração dos testes: herda tudo e liga o modo de teste do Flask
    """

    TESTING = True
