import pytest

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
