"""
tests/services/test_pedido_service.py

TESTES DO PedidoService (app / services / pedido_service.py) e do Carrinho
Meta da s5: "um pedido é criado, pago, confirmado, baixa o estoque e é finalizado".

Cenário: ver tests / services / conftest.py (1 bolo = 500 g de farinha + 395 g de leite; estoque 10000 g e 15800 g)
O preço do bolo vem da CalculadoraPreco (multiplicador 2,5 sobre o custo)

Como rodar só esse arquivo:   pytest tests/services/test_pedido_service.py -v
"""
from contextlib import contextmanager
from decimal import Decimal

import pytest

from app.exceptions import PedidoSemEstoqueError, TransicaoStatusError, ValidacaoError
from app.models.enums import FormaPagamento, StatusPedido, TipoEntrega
from app.models.opcao_personalizacao import OpcaoPersonalizacao
from app.models.produto import Produto
from app.services.baixa_estoque import BaixaEstoque
from app.services.pedido_service import Carrinho, PedidoService
from app.services.precificacao import CalculadoraPreco
from tests.services.conftest import CRIACAO, ENTREGA_OK


@pytest.fixture
def servico(estoque):
    return PedidoService(CalculadoraPreco(), BaixaEstoque(estoque))


@pytest.fixture
def carrinho(bolo):
    cesto = Carrinho()
    cesto.adicionar(bolo, 2)
    return cesto


@pytest.fixture
def pedido(servico, cliente, carrinho):
    return servico.criarPedido(cliente, carrinho, TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO)


def pagoEConfirmavel(servico, pedido):
    servico.enviarOrcamento(pedido)
    servico.registrarSinal(pedido, FormaPagamento.PIX)


# CARRINHO
def test_carrinho_novo_esta_vazio():
    assert Carrinho().vazio is True


def test_carrinho_adicionar_e_remover(bolo):
    cesto = Carrinho()
    linha = cesto.adicionar(bolo, 3)
    assert cesto.vazio is False and cesto.linhas == (linha,)
    cesto.remover(linha)
    assert cesto.vazio is True


def test_carrinho_recusa_produto_inativo(bolo):
    bolo.alternarAtivo()
    with pytest.raises(ValidacaoError, match="não está disponível"):
        Carrinho().adicionar(bolo, 1)


def test_carrinho_recusa_quantidade_invalida(bolo):
    with pytest.raises(ValidacaoError):
        Carrinho().adicionar(bolo, 0)


def test_carrinho_remover_linha_de_outro_carrinho(bolo):
    linha = Carrinho().adicionar(bolo, 1)
    with pytest.raises(ValidacaoError):
        Carrinho().remover(linha)


# CRIAÇÃO
def test_criar_pedido_fixa_precos_e_esvazia_o_carrinho(servico, cliente, carrinho, bolo):
    pedido = servico.criarPedido(cliente, carrinho, TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO)
    preco = CalculadoraPreco().precoUnitario(bolo)
    assert pedido.status is StatusPedido.SOLICITADO
    assert len(pedido.itens) == 1 and pedido.itens[0].preco_unitario == preco
    assert servico.total(pedido) == preco * 2
    assert carrinho.vazio is True


def test_criar_pedido_com_carrinho_vazio(servico, cliente):
    with pytest.raises(ValidacaoError, match="vazio"):
        servico.criarPedido(cliente, Carrinho(), TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO)


def test_criar_pedido_com_opcao_de_personalizacao(servico, cliente, bolo):
    opcao = OpcaoPersonalizacao("Brigadeiro", 3)
    bolo.adicionarOpcao(opcao)
    cesto = Carrinho()
    cesto.adicionar(bolo, 1, escolhas=[(opcao, 1)])
    pedido = servico.criarPedido(cliente, cesto, TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO)
    assert pedido.itens[0].custo_personalizacao == Decimal("3.00")


def test_criar_pedido_para_entrega_calcula_taxa_pela_distancia(servico, cliente, carrinho):
    endereco = cliente.enderecos[0]
    pedido = servico.criarPedido(cliente, carrinho, TipoEntrega.ENTREGA, ENTREGA_OK, endereco=endereco,
                                 distancia_km=3, data_criacao=CRIACAO)
    assert pedido.taxa_entrega == CalculadoraPreco().taxaEntrega(TipoEntrega.ENTREGA, 3)
    assert pedido.taxa_entrega > 0


def test_criar_pedido_entrega_sem_distancia(servico, cliente, carrinho):
    with pytest.raises(ValidacaoError, match="distância"):
        servico.criarPedido(cliente, carrinho, TipoEntrega.ENTREGA, ENTREGA_OK,
                            endereco=cliente.enderecos[0], data_criacao=CRIACAO)


def test_criar_pedido_com_prazo_insuficiente_nao_salva(estoque, cliente, carrinho):
    salvos = []
    servico = PedidoService(CalculadoraPreco(), BaixaEstoque(estoque), salvar_pedido=salvos.append)
    with pytest.raises(ValidacaoError, match="48h"):
        servico.criarPedido(cliente, carrinho, TipoEntrega.RETIRADA, CRIACAO.replace(day=3), data_criacao=CRIACAO)
    assert salvos == []


def test_criar_pedido_salva(estoque, cliente, carrinho):
    salvos = []
    servico = PedidoService(CalculadoraPreco(), BaixaEstoque(estoque), salvar_pedido=salvos.append)
    pedido = servico.criarPedido(cliente, carrinho, TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO)
    assert salvos == [pedido]


# VALORES
def test_valor_restante_e_metade_do_total(servico, pedido):
    assert servico.valorRestante(pedido) == servico.total(pedido) / 2


# CONFIRMAÇÃO E BAIXA
def test_confirmar_baixa_estoque_e_muda_status(servico, pedido, farinha, leite):
    pagoEConfirmavel(servico, pedido)
    movimentacoes = servico.confirmar(pedido)
    assert pedido.status is StatusPedido.CONFIRMADO
    assert len(movimentacoes) == 2
    assert farinha.quantidade_atual == Decimal("9000") and leite.quantidade_atual == Decimal("15010")


def test_confirmar_sem_sinal_nao_baixa_estoque(servico, pedido, farinha):
    servico.enviarOrcamento(pedido)
    with pytest.raises(ValidacaoError, match="sinal"):
        servico.confirmar(pedido)
    assert farinha.quantidade_atual == Decimal("10000")
    assert pedido.status is StatusPedido.ORCAMENTO


def test_confirmar_fora_do_fluxo_nao_baixa_estoque(servico, pedido, farinha):
    with pytest.raises(TransicaoStatusError):
        servico.confirmar(pedido)
    assert farinha.quantidade_atual == Decimal("10000")


def test_confirmar_sem_insumo_recusa_com_explicacao(estoque, cliente, bolo, farinha):
    servico = PedidoService(CalculadoraPreco(), BaixaEstoque(estoque))
    cesto = Carrinho()
    cesto.adicionar(bolo, 30)
    pedido = servico.criarPedido(cliente, cesto, TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO)
    pagoEConfirmavel(servico, pedido)
    with pytest.raises(PedidoSemEstoqueError, match="Farinha"):
        servico.confirmar(pedido)
    assert pedido.status is StatusPedido.ORCAMENTO
    assert farinha.quantidade_atual == Decimal("10000")


def test_confirmar_usa_a_transacao_e_salva_dentro_dela(estoque, cliente, carrinho):
    eventos = []

    @contextmanager
    def transacao():
        eventos.append("inicio")
        yield
        eventos.append("fim")

    servico = PedidoService(CalculadoraPreco(),
                            BaixaEstoque(estoque, lambda insumo, mov: eventos.append("gravou mov")),
                            salvar_pedido=lambda p: eventos.append("salvou pedido"), transacao=transacao)
    pedido = servico.criarPedido(cliente, carrinho, TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO)
    eventos.clear()
    pagoEConfirmavel(servico, pedido)
    eventos.clear()
    servico.confirmar(pedido)
    assert eventos == ["inicio", "gravou mov", "gravou mov", "salvou pedido", "fim"]


# IMUTABILIDADE
def test_pedido_confirmado_nao_aceita_novos_itens(servico, pedido, bolo):
    pagoEConfirmavel(servico, pedido)
    servico.confirmar(pedido)
    item = CalculadoraPreco().montarItem(bolo, 1)
    with pytest.raises(ValidacaoError, match="não pode mais ser alterado"):
        pedido.adicionarItem(item)
    with pytest.raises(ValidacaoError):
        pedido.removerItem(pedido.itens[0])
    with pytest.raises(ValidacaoError):
        pedido.definirTaxaEntrega(10)


# CANCELAMENTO
def test_cancelar_exige_motivo(servico, pedido):
    pagoEConfirmavel(servico, pedido)
    servico.confirmar(pedido)
    with pytest.raises(ValidacaoError):
        servico.cancelar(pedido, "")
    assert pedido.status is StatusPedido.CONFIRMADO


def test_cancelar_confirmado_guarda_o_motivo(servico, pedido):
    pagoEConfirmavel(servico, pedido)
    servico.confirmar(pedido)
    servico.cancelar(pedido, "Cliente desistiu")
    assert pedido.status is StatusPedido.CANCELADO
    assert pedido.motivo_cancelamento == "Cliente desistiu"


def test_cancelar_antes_de_confirmar_nao_e_permitido(servico, pedido):
    with pytest.raises(TransicaoStatusError):
        servico.cancelar(pedido, "Cliente desistiu")


# AVANÇAR
def test_avancar_recusa_confirmado_e_cancelado(servico, pedido):
    with pytest.raises(ValidacaoError, match="confirmar\\(\\)"):
        servico.avancar(pedido, StatusPedido.CONFIRMADO)
    with pytest.raises(ValidacaoError, match="cancelar"):
        servico.avancar(pedido, StatusPedido.CANCELADO)


def test_avancar_aceita_texto_do_banco(servico, pedido):
    servico.avancar(pedido, "orcamento")
    assert pedido.status is StatusPedido.ORCAMENTO


# FLUXO COMPLETO (meta da semana 5)
def test_fluxo_completo_criado_pago_confirmado_baixa_e_finalizado(servico, pedido, farinha, leite):
    servico.enviarOrcamento(pedido)
    servico.registrarSinal(pedido, FormaPagamento.PIX)
    servico.confirmar(pedido)
    servico.avancar(pedido, StatusPedido.EM_PRODUCAO)
    servico.avancar(pedido, StatusPedido.PRONTO)
    servico.avancar(pedido, StatusPedido.ENTREGUE)
    with pytest.raises(ValidacaoError):                     # ainda falta pagar o restante
        servico.avancar(pedido, StatusPedido.FINALIZADO)
    servico.registrarPagamentoRestante(pedido, FormaPagamento.DINHEIRO)
    servico.avancar(pedido, StatusPedido.FINALIZADO)
    assert pedido.status is StatusPedido.FINALIZADO
    assert pedido.pagamento.quitado is True
    assert farinha.quantidade_atual == Decimal("9000")
    assert leite.quantidade_atual == Decimal("15010")