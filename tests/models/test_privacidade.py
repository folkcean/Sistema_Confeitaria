import pytest

from app.exceptions import AcessoNegadoError

CHAVES_COMPLETAS = {
    "nome",
    "apelido",
    "email",
    "telefone",
    "cpf",
    "data_nascimento",
    "vip",
    "instagram",
    "restricoes_alimentares",
    "observacoes",
    "preferencias",
    "enderecos",
}

CHAVES_OPERACIONAIS = {"apelido", "telefone", "restricoes_alimentares", "enderecos"}


# Quem vê o quê (cliente.acessoAosDados)
def test_administrador_ve_o_dict_completo_com_cpf_em_digitos(cliente, administrador):
    dados = cliente.acessoAosDados(administrador)

    assert set(dados) == CHAVES_COMPLETAS
    assert dados["cpf"] == "52998224725"


def test_funcionario_ve_so_os_dados_operacionais(cliente, funcionario):
    dados = cliente.acessoAosDados(funcionario)

    assert set(dados) == CHAVES_OPERACIONAIS
    assert "cpf" not in dados


def test_proprio_cliente_ve_o_dict_completo(cliente):
    dados = cliente.acessoAosDados(cliente)

    assert set(dados) == CHAVES_COMPLETAS
    assert dados["cpf"] == "52998224725"


def test_outro_cliente_nao_ve_dados_de_cliente(cliente, outro_cliente):
    with pytest.raises(AcessoNegadoError, match="próprios dados"):
        cliente.acessoAosDados(outro_cliente)


# CPF (obterCpf)
def test_funcionario_nao_obtem_cpf_de_cliente(cliente, funcionario):
    with pytest.raises(AcessoNegadoError, match="Apenas o próprio usuário"):
        cliente.obterCpf(funcionario)


def test_outro_cliente_nao_obtem_cpf_de_cliente(cliente, outro_cliente):
    with pytest.raises(AcessoNegadoError, match="Apenas o próprio usuário"):
        cliente.obterCpf(outro_cliente)


def test_administrador_consulta_cpf_do_cliente(cliente, administrador):
    assert administrador.consultarCpfCliente(cliente) == "52998224725"


def test_cliente_sem_cpf_devolve_none_para_o_administrador(
    outro_cliente, administrador
):
    assert administrador.consultarCpfCliente(outro_cliente) is None
