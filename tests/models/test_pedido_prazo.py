"""
tests/models/test_pedido_prazo.py

TESTES DA INTEGRAÇÃO Pedido <-> PrazoPedido (s5): Produto.pronta_entrega, Pedido.validarPrazo
e Pedido.exigirConfirmavel

Como rodar sé esse arquivo:   pytest tests/models/test_pedido_prazo.py -v
"""
from datetime import datetime

import pytest

from app.exceptions import TransicaoStatusError, ValidacaoError
from app.models.cliente import Cliente
from app.models.enums import FormaPagamento, StatusPedido, TipoEntrega
from app.models.pedido import ItemPedido, Pedido
from app.models.produto import Produto

CRIACAO = datetime(2026, 11, 2, 10, 0)


@pytest.fixture
def cliente():
    return Cliente("Maria Silva", "maria@email.com", "22999998888", None)


def pedidoCom(cliente, produto, entrega):
    pedido = Pedido(cliente, TipoEntrega.RETIRADA, entrega, data_criacao=CRIACAO)
    pedido.adicionarItem(ItemPedido(produto, 1, 50, 20))
    return pedido


# Produto.pronta_entrega
@pytest.mark.parametrize("texto, esperado", [
    ("Pronta entrega", True), ("pronta_entrega", True), ("  PRONTA ENTREGA ", True),
    ("Sob encomenda", False), ("encomenda", False),
])
def test_produto_pronta_entrega(texto, esperado):
    assert Produto("Bolo", 50, disponibilidade=texto).pronta_entrega is esperado


# validarPrazo
def test_encomenda_respeita_antecedencia(cliente):
    pedido = pedidoCom(cliente, Produto("Bolo", 50), datetime(2026, 11, 3, 10, 0))
    with pytest.raises(ValidacaoError, match="48h"):
        pedido.validarPrazo()


def test_encomenda_com_prazo_suficiente(cliente):
    pedidoCom(cliente, Produto("Bolo", 50), datetime(2026, 11, 4, 10, 0)).validarPrazo()


def test_pronta_entrega_fora_do_horario(cliente):
    produto = Produto("Brigadeiro", 5, disponibilidade="Pronta entrega")
    pedido = Pedido(cliente, TipoEntrega.RETIRADA, datetime(2026, 11, 2, 18, 30),
                    data_criacao=datetime(2026, 11, 2, 17, 30))
    pedido.adicionarItem(ItemPedido(produto, 1, 5, 2))
    with pytest.raises(ValidacaoError, match="pronta entrega"):
        pedido.validarPrazo()


def test_pronta_entrega_no_horario(cliente):
    produto = Produto("Brigadeiro", 5, disponibilidade="Pronta entrega")
    pedido = Pedido(cliente, TipoEntrega.RETIRADA, datetime(2026, 11, 2, 12, 0), data_criacao=CRIACAO)
    pedido.adicionarItem(ItemPedido(produto, 1, 5, 2))
    pedido.validarPrazo()


# exigirConfirmavel
def test_exigir_confirmavel_sem_sinal_falha_e_nao_altera(cliente):
    pedido = pedidoCom(cliente, Produto("Bolo", 50), datetime(2026, 11, 10, 10, 0))
    pedido.avancarStatus(StatusPedido.ORCAMENTO)
    with pytest.raises(ValidacaoError, match="sinal"):
        pedido.exigirConfirmavel()
    assert pedido.status is StatusPedido.ORCAMENTO


def test_exigir_confirmavel_com_sinal_passa_e_nao_confirma(cliente):
    pedido = pedidoCom(cliente, Produto("Bolo", 50), datetime(2026, 11, 10, 10, 0))
    pedido.avancarStatus(StatusPedido.ORCAMENTO)
    pedido.registrarSinal(FormaPagamento.PIX)
    pedido.exigirConfirmavel()
    assert pedido.status is StatusPedido.ORCAMENTO


def test_exigir_confirmavel_fora_do_fluxo(cliente):
    pedido = pedidoCom(cliente, Produto("Bolo", 50), datetime(2026, 11, 10, 10, 0))
    with pytest.raises(TransicaoStatusError):
        pedido.exigirConfirmavel()