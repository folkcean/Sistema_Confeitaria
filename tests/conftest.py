"""
tests / conftest.py

Fixtures que valem para TODAS as pastas de teste:
    - objetos de exemplo dos models (cliente, funcionario, administrador, endereco...)
    - o banco de teste (conexao, banco, seed), usado em tests/db/ e em tests/rotas/

As fixtures do banco moravam em tests/db/conftest.py. Subiram para cá porque os testes de
rota (tests/rotas/) também precisam delas, e um conftest.py só vale para a pasta dele e as
de baixo
"""

import os
from pathlib import Path

import psycopg
import pytest
from dotenv import load_dotenv

from app.models.administrador import Administrador
from app.models.cliente import Cliente
from app.models.endereco import Endereco
from app.models.funcionario import Funcionario
from app.models.senha import Senha


@pytest.fixture
def senha_forte():
    """Senha que passa em todas as regras de força"""
    return "Bolo@2026"


@pytest.fixture
def cliente(senha_forte):
    """Cliente completo: Ana Souza, com e-mail, CPF válido, apelido e senha"""
    return Cliente(
        "Ana Souza",
        "ana@exemplo.com",
        "(22) 99999-0001",
        "529.982.247-25",
        apelido="Aninha",
        id_usuario=10,
        senha=Senha.criar(senha_forte),
    )


@pytest.fixture
def outro_cliente():
    """Cliente mínimo: Beto Lima, sem e-mail, sem CPF e sem senha"""
    return Cliente("Beto Lima", None, "22999990004", None, id_usuario=11)


@pytest.fixture
def funcionario():
    """Funcionário: João Viana, confeiteiro, sem CPF"""
    return Funcionario(
        "João Viana",
        "joao@exemplo.com",
        "22999990002",
        None,
        cargo="confeiteiro",
        data_nascimento="1999-07-02",
        id_usuario=2,
    )


@pytest.fixture
def administrador():
    """Administrador: Rosângela Crespo, com CPF válido"""
    return Administrador(
        "Rosângela Crespo",
        "rosangela@exemplo.com",
        "22999990003",
        "123.456.789-09",
        id_usuario=1,
    )


@pytest.fixture
def endereco():
    """Endereço de exemplo em Campos dos Goytacazes, ainda sem dono"""
    return Endereco(
        "Rua Barão de Miracema",
        "100",
        "Centro",
        "Campos dos Goytacazes",
        "28035-000",
        complemento="Apto 2",
    )


# ------------------------------------------------------------------ Banco de dados
# Raiz do projeto: este arquivo está em tests/, um .parent a mais sobe para a raiz
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

SEED = Path(__file__).resolve().parent / "db" / "DB_fill.sql"


@pytest.fixture(scope="session")
def conexao():
    """
    Uma conexão só para todos os testes (abrir conexão é caro)

    Não use sozinha: peça `banco` ou `seed` junto, que são elas que desfazem tudo no fim
    """
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
    """
    Cursor do teste, dentro de uma transação que é desfeita no fim (rollback)

    O `select 1` abre a transação logo no começo. Sem ele, o primeiro `with conexao.transaction()`
    do código (o _transacao dos repositórios) abriria a transação dele e daria COMMIT de verdade
    no seu banco. Com a transação já aberta, esse `with` vira um SAVEPOINT dentro dela
    """
    # Cria um operador(cursor) que vai realizar comandos dentro do banco.
    with conexao.cursor() as cur:
        cur.execute("select 1")
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


@pytest.fixture
def hoje_no_banco(banco):
    """
    A data de hoje para o PostgreSQL

    O DB_fill.sql monta as datas dos pedidos com now() do banco. O relógio do banco (no Docker,
    em UTC) pode estar num dia diferente do seu entre 21h e meia-noite: comparar com esta data,
    e não com date.today(), deixa os testes de relatório iguais em qualquer horário
    """
    banco.execute("select current_date")
    return banco.fetchone()[0]
