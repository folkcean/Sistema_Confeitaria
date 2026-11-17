"""
tests / services / test_pagamento_online.py

ServicoPagamentoOnline (app / services / pagamento_online.py) com o GatewayFalso: sem internet e sem banco

Cenário: pedido 6 com um bolo de R$ 100,00 (sinal de R$ 50,00 e restante de R$ 50,00), retirada
    - sinal:    pedido em orçamento, aguardando o sinal
    - restante: pedido confirmado, com o sinal já pago
Como rodar só esse arquivo:   pytest tests/services/test_pagamento_online.py -v
"""
from decimal import Decimal

import pytest

from app.exceptions import ValidacaoError
from app.models.enums import FormaPagamento, StatusPedido, TipoEntrega
from app.models.pedido import ItemPedido, Pedido
from app.services.pagamento_online import RESTANTE, SINAL, ServicoPagamentoOnline
from tests.falsos import GatewayFalso
from tests.services.conftest import CRIACAO, ENTREGA_OK


def montarPedido(cliente, bolo, status):
    """Pedido de R$ 100,00 (sem taxa) no status pedido"""
    pedido = Pedido(cliente, TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO,
                    status=status, id_pedido=6)
    pedido.adicionarItem(ItemPedido(bolo, 1, preco_unitario=Decimal("100.00"), custo_unitario=Decimal("40.00")))
    return pedido


@pytest.fixture
def gateway():
    return GatewayFalso()


@pytest.fixture
def salvos():
    """Lista dos pedidos que o serviço mandou gravar"""
    return []


@pytest.fixture
def servico(gateway, salvos):
    return ServicoPagamentoOnline(gateway, salvos.append)


@pytest.fixture
def pedido(cliente, bolo):
    return montarPedido(cliente, bolo, StatusPedido.ORCAMENTO)


@pytest.fixture
def pedido_confirmado(cliente, bolo):
    """Montado em orçamento (só aí aceita itens), com o sinal pago (dinheiro) e depois confirmado"""
    pedido = montarPedido(cliente, bolo, StatusPedido.ORCAMENTO)
    pedido.registrarSinal(FormaPagamento.DINHEIRO)
    pedido.avancarStatus(StatusPedido.CONFIRMADO)
    return pedido


# Sinal

def test_cria_o_pix_com_o_valor_do_sinal_e_vincula_o_id(servico, gateway, salvos, pedido):
    pix = servico.obterPix(pedido, SINAL)

    assert gateway.ultimo_valor == Decimal("50.00")
    assert pix.status == "PENDING" and pix.paga is False
    assert pedido.pagamento.cobranca_sinal == pix.id
    assert salvos == [pedido]


def test_chamar_de_novo_com_o_pix_pendente_devolve_o_mesmo(servico, pedido):
    primeiro = servico.obterPix(pedido, SINAL)
    segundo = servico.obterPix(pedido, SINAL)

    assert segundo.id == primeiro.id


def test_depois_de_pago_registra_o_sinal(servico, salvos, pedido):
    servico.obterPix(pedido, SINAL)
    servico.simularPix(pedido, SINAL)

    pix = servico.obterPix(pedido, SINAL)

    assert pix.paga is True
    assert pedido.pagamento.sinal_pago is True
    assert pedido.pagamento.forma_sinal is FormaPagamento.PIX
    assert len(salvos) == 2


def test_pix_vencido_gera_outro(servico, gateway, pedido):
    vencido = servico.obterPix(pedido, SINAL)
    gateway.vencer(vencido.id)

    novo = servico.obterPix(pedido, SINAL)

    assert novo.id != vencido.id
    assert pedido.pagamento.cobranca_sinal == novo.id


def test_pedido_sem_orcamento_nao_chama_o_gateway(servico, gateway, cliente, bolo):
    pedido = montarPedido(cliente, bolo, StatusPedido.SOLICITADO)

    with pytest.raises(ValidacaoError, match="orçamento"):
        servico.obterPix(pedido, SINAL)
    assert gateway.chamadas == 0


def test_simular_sem_pix_gerado_recusa(servico, pedido):
    with pytest.raises(ValidacaoError, match="Gere o Pix"):
        servico.simularPix(pedido, SINAL)


# Restante

def test_cria_o_pix_do_restante_com_outra_referencia(servico, gateway, pedido_confirmado):
    pix = servico.obterPix(pedido_confirmado, RESTANTE)

    assert gateway.ultimo_valor == Decimal("50.00")
    assert pedido_confirmado.pagamento.cobranca_restante == pix.id
    assert pedido_confirmado.pagamento.cobranca_sinal is None


def test_depois_de_pago_quita_o_pedido(servico, pedido_confirmado):
    servico.obterPix(pedido_confirmado, RESTANTE)
    servico.simularPix(pedido_confirmado, RESTANTE)

    pix = servico.obterPix(pedido_confirmado, RESTANTE)

    assert pix.paga is True
    assert pedido_confirmado.pagamento.quitado is True
    assert pedido_confirmado.pagamento.forma_restante is FormaPagamento.PIX
    # O sinal continua com a forma de antes
    assert pedido_confirmado.pagamento.forma_sinal is FormaPagamento.DINHEIRO


def test_restante_antes_de_confirmar_nao_chama_o_gateway(servico, gateway, pedido):
    with pytest.raises(ValidacaoError, match="confirmado"):
        servico.obterPix(pedido, RESTANTE)
    assert gateway.chamadas == 0


def test_restante_ja_quitado_recusa(servico, gateway, pedido_confirmado):
    pedido_confirmado.registrarPagamentoRestante(FormaPagamento.CARTAO)

    with pytest.raises(ValidacaoError, match="já foi pago"):
        servico.obterPix(pedido_confirmado, RESTANTE)
    assert gateway.chamadas == 0
