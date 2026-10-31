import os
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")

SEED = Path(__file__).resolve().parent / "DB_fill.sql"


@pytest.fixture(scope="session")
def conexao():
    # Preenchendo as credenciais do banco de dados.
    try:
        conexao = psycopg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            dbname=os.environ["POSTGRES_DB"],
        )
    except psycopg.OperationalError as erro:
        # Conexão com banco de dados falhou.
        pytest.skip(f"Conexão com o banco de dados falhou.\n Rode 'docker compose up -d'.\n Detalhe: {erro}")
    yield conexao
    conexao.close()


@pytest.fixture
def banco(conexao):
    # Cria um operador(cursor) que vai realizar comandos dentro do banco.
    with conexao.cursor() as cur:
        yield cur
    conexao.rollback()


@pytest.fixture
def seed(banco):
    """
    Carrega o DB_fill.sql dentro da transação do teste.

    Como o `banco` desfaz tudo no final (rollback), o seed vale só durante o teste:
    os testes não dependem do que está no seu banco e não apagam os seus dados
    """
    banco.execute(SEED.read_text(encoding="utf-8"))
    return banco
