"""Fixtures compartilhadas pelos testes que usam o banco de dados.

Os testes conectam no PostgreSQL do Docker com as credenciais do .env.
Cada teste roda dentro de uma transacao que e desfeita no final,
entao nenhum teste deixa dados no banco nem interfere em outro.
"""
import os
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv

# Le o .env da raiz do projeto (a pasta acima de tests/).
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@pytest.fixture(scope="session")
def conexao():
    #Preenchendo as credenciais do banco de dados.
    try:
        conexao = psycopg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            dbname=os.environ["POSTGRES_DB"],
        )
    except psycopg.OperationalError as erro:
        #Conexão com banco de dados falhou.
        pytest.skip(f"Conexão com o banco de dados falhou.\n Rode 'docker compose up -d'.\n Detalhe: {erro}")
    yield conexao
    conexao.close()


@pytest.fixture
def banco(conexao):
    #Cria um operador(cursor) que vai realizar comandos dentro do banco.
    with conexao.cursor() as cur:
        yield cur
    conexao.rollback()
