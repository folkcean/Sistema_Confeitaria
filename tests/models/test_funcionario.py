from datetime import date

import pytest

from app.exceptions import ValidacaoError
from app.models.enums import Perfil, StatusPedido
from app.models.funcionario import Funcionario


class PedidoEspiao:
    """Pedido de mentira: anota os status que recebeu"""

    def __init__(self):
        self.recebidos = []

    def avancarStatus(self, novo_status):
        self.recebidos.append(novo_status)


class EstoqueFalso:
    """Estoque de mentira: resumo fixo e ajustes anotados"""

    def __init__(self):
        self.ajustes = []

    def resumo(self):
        return [{"ingrediente": "farinha", "quantidade": 5000}]

    def ajustarManual(self, ingrediente, nova_quantidade, motivo):
        self.ajustes.append((ingrediente, nova_quantidade, motivo))


def novo_funcionario(**kwargs):
    """Funcionário mínimo; cada teste troca só o campo que quer testar"""
    kwargs.setdefault("cargo", "confeiteiro")
    kwargs.setdefault("data_nascimento", "1999-07-02")
    return Funcionario("João Viana", None, "22999990002", None, **kwargs)


@pytest.mark.parametrize("data_nascimento", [None, ""], ids=repr)
def test_funcionario_sem_data_nascimento_levanta_erro(data_nascimento):
    with pytest.raises(ValidacaoError, match="obrigatória para funcionários"):
        novo_funcionario(data_nascimento=data_nascimento)


def test_data_contratacao_padrao_e_hoje():
    assert novo_funcionario().data_contratacao == date.today()


def test_data_contratacao_informada_e_respeitada():
    funcionario = novo_funcionario(data_contratacao="2026-01-15")

    assert funcionario.data_contratacao == date(2026, 1, 15)


def test_cargo_vazio_levanta_erro():
    with pytest.raises(ValidacaoError, match="obrigatório"):
        novo_funcionario(cargo="")


def test_funcionario_tem_perfil_funcionario_e_nao_acessa_dados_sensiveis(funcionario):
    assert funcionario.perfil is Perfil.FUNCIONARIO
    assert funcionario.acessa_dados_sensiveis is False


def test_atualizar_status_pedido_repassa_o_status_ao_pedido(funcionario):
    pedido = PedidoEspiao()

    funcionario.atualizarStatusPedido(pedido, StatusPedido.PRONTO)

    assert pedido.recebidos == [StatusPedido.PRONTO]


def test_consultar_estoque_devolve_o_resumo_do_estoque(funcionario):
    resumo = funcionario.consultarEstoque(EstoqueFalso())

    assert resumo == [{"ingrediente": "farinha", "quantidade": 5000}]
