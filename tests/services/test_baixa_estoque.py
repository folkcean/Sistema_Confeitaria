"""
tests / services / test_baixa_estoque.py

TESTES DA BaixaEstoque (app / services / baixa_estoque.py). Usa as fixtures de tests / services / conftest.py.
1 bolo = 0,500 kg de farinha + 1,000 lata de leite condensado.

Como rodar so esse arquivo:   pytest tests/services/test_baixa_estoque.py -v
"""
from decimal import Decimal

import pytest

from app.exceptions import EstoqueInsuficienteError, PedidoSemEstoqueError
from app.models.enums import TipoEntrega
from app.models.pedido import ItemPedido, Pedido
from app.services.baixa_estoque import BaixaEstoque
from tests.services.conftest import CRIACAO, ENTREGA_OK


def pedidoDeBolos(cliente, bolo, quantidade):
    pedido = Pedido(cliente, TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO)
    pedido.adicionarItem(ItemPedido(bolo, quantidade, 50, 20))
    return pedido


def test_necessidades_multiplicam_pela_quantidade(cliente, bolo, estoque):
    pedido = pedidoDeBolos(cliente, bolo, 3)
    necessidades = BaixaEstoque(estoque).necessidadesDoPedido(pedido)
    assert {insumo.nome: qtd for insumo, qtd in necessidades} == {
        "Farinha": Decimal("1500"), "Leite condensado": Decimal("1185")}


def test_executar_desconta_os_insumos(cliente, bolo, estoque, farinha, leite):
    BaixaEstoque(estoque).executar(pedidoDeBolos(cliente, bolo, 4))
    assert farinha.quantidade_atual == Decimal("8000")      # 10000 g - 4 x 500 g
    assert leite.quantidade_atual == Decimal("14220")       # 15800 g - 4 x 395 g


def test_executar_devolve_movimentacoes_ligadas_ao_pedido(cliente, bolo, estoque):
    pedido = pedidoDeBolos(cliente, bolo, 1)
    pedido.atribuirID(7)
    movimentacoes = BaixaEstoque(estoque).executar(pedido)
    assert len(movimentacoes) == 2
    assert {m.id_pedido for m in movimentacoes} == {7}


def test_executar_grava_cada_movimentacao(cliente, bolo, estoque):
    gravadas = []
    baixa = BaixaEstoque(estoque, lambda insumo, mov: gravadas.append((insumo.nome, mov.quantidade)))
    baixa.executar(pedidoDeBolos(cliente, bolo, 2))
    assert sorted(gravadas) == [("Farinha", Decimal("1000")), ("Leite condensado", Decimal("790"))]


def test_falta_de_insumo_recusa_sem_descontar_nada(cliente, bolo, estoque, farinha, leite):
    with pytest.raises(PedidoSemEstoqueError) as erro:
        BaixaEstoque(estoque).executar(pedidoDeBolos(cliente, bolo, 30))   # leite: 11850 g ok; farinha: 15000 g > 10000 g
    assert farinha.quantidade_atual == Decimal("10000")
    assert leite.quantidade_atual == Decimal("15800")
    assert erro.value.faltas == [{"insumo": "Farinha", "unidade": "g", "faltam": Decimal("5000")}]


def test_mensagem_explica_o_que_falta_e_o_que_fazer(cliente, bolo, estoque):
    with pytest.raises(PedidoSemEstoqueError, match="falta de insumos: Farinha \\(faltam 5000.000 g\\)") as erro:
        BaixaEstoque(estoque).executar(pedidoDeBolos(cliente, bolo, 30))
    assert "Reponha o estoque" in str(erro.value)


def test_pedido_sem_estoque_e_um_estoque_insuficiente(cliente, bolo, estoque):
    with pytest.raises(EstoqueInsuficienteError):
        BaixaEstoque(estoque).executar(pedidoDeBolos(cliente, bolo, 30))


def test_verificar_nao_altera_estoque(cliente, bolo, estoque, farinha):
    faltas = BaixaEstoque(estoque).verificar(pedidoDeBolos(cliente, bolo, 30))
    assert len(faltas) == 1
    assert farinha.quantidade_atual == Decimal("10000")


def test_verificar_pedido_possivel_devolve_lista_vazia(cliente, bolo, estoque):
    assert BaixaEstoque(estoque).verificar(pedidoDeBolos(cliente, bolo, 2)) == []


def test_itens_do_mesmo_produto_somam_antes_de_conferir(cliente, bolo, estoque, farinha):
    pedido = Pedido(cliente, TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO)
    pedido.adicionarItem(ItemPedido(bolo, 12, 50, 20))
    pedido.adicionarItem(ItemPedido(bolo, 12, 50, 20, personalizacao="Parabéns"))
    with pytest.raises(PedidoSemEstoqueError):       # cada item sozinho cabe (6000 g), juntos não (12000 g)
        BaixaEstoque(estoque).executar(pedido)
    assert farinha.quantidade_atual == Decimal("10000")