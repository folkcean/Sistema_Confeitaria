"""
tests / db / test_email_verificado_repositorio.py

Coluna usuario.email_verificado (db/update/001_adiciona_email_verificado.sql) e o que os repositórios fazem com ela.
Precisa do banco com o script 001 aplicado.

COMO RODAR SÓ ESTE ARQUIVO:   pytest tests/db/test_email_verificado_repositorio.py -v
"""
import pytest

from app.models import Cliente
from app.repositories.clientes_rep import RepositorioClientes
from app.repositories.usuarios_rep import RepositorioUsuarios


@pytest.fixture
def usuarios(conexao, seed):
    return RepositorioUsuarios(lambda: conexao)


@pytest.fixture
def clientes(conexao, seed):
    return RepositorioClientes(lambda: conexao)


def test_contas_do_seed_nao_estao_verificadas(usuarios):
    assert usuarios.buscarPorEmail("ana@exemplo.com").email_verificado is False


def test_marcar_email_verificado_grava_no_banco(usuarios):
    ana = usuarios.buscarPorEmail("ana@exemplo.com")
    ana.marcarEmailVerificado()

    usuarios.marcarEmailVerificado(ana)

    assert usuarios.buscarPorId(ana.id).email_verificado is True


def test_cliente_novo_nasce_nao_verificado(clientes, usuarios):
    novo = Cliente("Fulana de Tal", "fulana@exemplo.com", "22988887777", None)

    clientes.cadastrarCliente(novo)

    assert usuarios.buscarPorId(novo.id).email_verificado is False


def test_trocar_o_email_do_cliente_zera_a_confirmacao_no_banco(clientes, usuarios):
    ana = usuarios.buscarPorEmail("ana@exemplo.com")
    ana.marcarEmailVerificado()
    clientes.atualizarCliente(ana)
    assert usuarios.buscarPorId(ana.id).email_verificado is True

    ana.email = "ana.nova@exemplo.com"
    clientes.atualizarCliente(ana)

    recarregada = usuarios.buscarPorId(ana.id)
    assert recarregada.email == "ana.nova@exemplo.com"
    assert recarregada.email_verificado is False


def test_editar_outro_dado_mantem_a_confirmacao(clientes, usuarios):
    ana = usuarios.buscarPorEmail("ana@exemplo.com")
    ana.marcarEmailVerificado()
    clientes.atualizarCliente(ana)

    ana.nome = "Ana Souza Lima"
    clientes.atualizarCliente(ana)

    assert usuarios.buscarPorId(ana.id).email_verificado is True