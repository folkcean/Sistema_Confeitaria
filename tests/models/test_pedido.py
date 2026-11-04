"""
tests/models/test_pedido.py

Datas fixas: o pedido é criado em 02/11/2026 10:00 (parâmetro `data_criacao`), assim o teste de prazo mínimo
não depende do relógio do computador. O produto padrão pede 48 h de antecedência.

Como rodar só esse arquivo:   pytest tests/models/test_pedido.py -v
"""
from datetime import datetime
from decimal import Decimal

import pytest

from app.exceptions import TransicaoStatusError, ValidacaoError
from app.models.cliente import Cliente
from app.models.endereco import Endereco
from app.models.enums import FormaPagamento, StatusPagamento, StatusPedido, TipoEntrega
from app.models.opcao_personalizacao import OpcaoPersonalizacao
from app.models.pedido import ItemPedido, ItemPedidoOpcao, Pagamento, Pedido
from app.models.produto import Produto

CRIACAO = datetime(2026, 11, 2, 10, 0)
ENTREGA_OK = datetime(2026, 11, 10, 15, 0)          # 8 dias depois: respeita qualquer prazo


# FIXTURES
@pytest.fixture
def cliente():
    """Cliente com um endereço cadastrado."""
    maria = Cliente("Maria Silva", "maria@email.com", "22999998888", None)
    maria.adicionarEndereco(Endereco("Rua A", "10", "Centro", "Campos", "28000-000"))
    return maria


@pytest.fixture
def produto():
    """Produto que pede 48 h de antecedência (padrão do DER) e tem a opção 'Brigadeiro' (R$ 3,00)"""
    bolo = Produto("Bolo", 50)
    bolo.adicionarOpcao(OpcaoPersonalizacao("Brigadeiro", 3))
    return bolo


@pytest.fixture
def pedido(cliente):
    """Pedido de retirada, ainda vazio"""
    return Pedido(cliente, TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO)


@pytest.fixture
def pedido_com_item(pedido, produto):
    """Pedido de retirada com 2 bolos de R$ 50,00 = R$ 100,00"""
    pedido.adicionarItem(ItemPedido(produto, 2, 50, 20))
    return pedido


@pytest.fixture
def outro_pedido(cliente):
    """Um SEGUNDO pedido, diferente de `pedido`. (As fixtures `pedido` e `pedido_com_item` são o MESMO objeto
    dentro de um teste, porque `pedido_com_item` recebe `pedido` por parâmetro; por isso precisamos de outro.)"""
    return Pedido(cliente, TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO)


def confirmar(pedido):
    """Leva o pedido até Confirmado pelo caminho normal (orçamento -> sinal -> confirmado)"""
    pedido.avancarStatus(StatusPedido.ORCAMENTO)
    pedido.registrarSinal(FormaPagamento.PIX)
    pedido.avancarStatus(StatusPedido.CONFIRMADO)


# PAGAMENTO
def test_pagamento_novo_aguarda_sinal():
    p = Pagamento()
    assert p.status is StatusPagamento.AGUARDANDO_SINAL
    assert p.sinal_pago is False
    assert p.quitado is False
    assert p.forma_sinal is None


def test_sinal_e_restante_sao_metade():
    p = Pagamento()
    assert p.sinal(Decimal("101.00")) == Decimal("50.50")
    assert p.restante(Decimal("101.00")) == Decimal("50.50")


def test_sinal_e_restante_sempre_somam_o_total():
    """100,01: metade 50,005 arredonda para 50,01; o restante é o que sobra (50,00). Sem perder centavo"""
    p = Pagamento()
    total = Decimal("100.01")
    assert p.sinal(total) == Decimal("50.01")
    assert p.sinal(total) + p.restante(total) == total


def test_fluxo_de_pagamento_completo():
    p = Pagamento()
    p.registrarSinal(FormaPagamento.PIX)
    assert p.status is StatusPagamento.SINAL_PAGO
    assert p.sinal_pago is True and p.quitado is False
    p.registrarRestante("dinheiro")                      # aceita o texto do banco
    assert p.status is StatusPagamento.PAGO
    assert p.quitado is True
    assert p.forma_restante is FormaPagamento.DINHEIRO


def test_valor_em_aberto_em_cada_status():
    total = Decimal("100.00")
    p = Pagamento()
    assert p.valorEmAberto(total) == Decimal("100.00")
    p.registrarSinal(FormaPagamento.PIX)
    assert p.valorEmAberto(total) == Decimal("50.00")
    p.registrarRestante(FormaPagamento.CARTAO)
    assert p.valorEmAberto(total) == Decimal("0.00")


def test_sinal_nao_pode_ser_pago_duas_vezes():
    p = Pagamento()
    p.registrarSinal(FormaPagamento.PIX)
    with pytest.raises(ValidacaoError):
        p.registrarSinal(FormaPagamento.PIX)


def test_restante_exige_sinal_antes():
    with pytest.raises(ValidacaoError):
        Pagamento().registrarRestante(FormaPagamento.PIX)


def test_restante_nao_pode_ser_pago_duas_vezes():
    p = Pagamento()
    p.registrarSinal(FormaPagamento.PIX)
    p.registrarRestante(FormaPagamento.PIX)
    with pytest.raises(ValidacaoError):
        p.registrarRestante(FormaPagamento.PIX)


@pytest.mark.parametrize("forma", ["cheque", "", None])
def test_forma_de_pagamento_invalida(forma):
    with pytest.raises(ValidacaoError):
        Pagamento().registrarSinal(forma)


def test_pagamento_recarregado_do_banco():
    p = Pagamento("sinal_pago", "pix", None)
    assert p.status is StatusPagamento.SINAL_PAGO
    assert p.forma_sinal is FormaPagamento.PIX


# ITEM PEDIDO OPÇÃO
def test_opcao_do_item_copia_o_custo_atual():
    opcao = OpcaoPersonalizacao("Brigadeiro", 3)
    escolha = ItemPedidoOpcao(opcao, 4)
    assert escolha.custo_cobrado == Decimal("3.00")
    assert escolha.subtotal == Decimal("12.00")


def test_custo_cobrado_fica_fixado_se_a_opcao_mudar_de_preco():
    opcao = OpcaoPersonalizacao("Brigadeiro", 3)
    escolha = ItemPedidoOpcao(opcao, 4)
    opcao.alterarCusto(10)
    assert escolha.custo_cobrado == Decimal("3.00")


def test_custo_cobrado_zero_informado_e_respeitado():
    """Zero é um valor válido (brinde): não pode ser confundido com 'não informado'"""
    escolha = ItemPedidoOpcao(OpcaoPersonalizacao("Brinde", 5), 1, custo_cobrado=0)
    assert escolha.custo_cobrado == Decimal("0.00")


@pytest.mark.parametrize("quantidade", [0, -1, 1.5, "2", True])
def test_quantidade_da_opcao_invalida(quantidade):
    with pytest.raises(ValidacaoError):
        ItemPedidoOpcao(OpcaoPersonalizacao("X", 1), quantidade)


# ITEM PEDIDO
def test_valores_do_item(produto):
    item = ItemPedido(produto, 3, "50", "20")
    assert item.subtotal_bruto == Decimal("150.00")
    assert item.custo_total == Decimal("60.00")
    assert item.custo_personalizacao == Decimal("0.00")
    assert item.subtotal == Decimal("150.00")
    assert item.desconto == Decimal("0.00")


def test_item_com_personalizacao_e_desconto(produto):
    item = ItemPedido(produto, 2, 50, 20, desconto=10)
    item.adicionarOpcao(produto.opcoes[0], 4)           # 4 brigadeiros x R$ 3,00 = R$ 12,00
    assert item.custo_personalizacao == Decimal("12.00")
    assert item.subtotal == Decimal("102.00")           # 100 + 12 - 10


@pytest.mark.parametrize("quantidade", [0, -1, 1.5, "2"])
def test_quantidade_do_item_invalida(produto, quantidade):
    with pytest.raises(ValidacaoError):
        ItemPedido(produto, quantidade, 50, 20)


def test_desconto_maior_que_o_item_e_recusado(produto):
    with pytest.raises(ValidacaoError):
        ItemPedido(produto, 1, 50, 20, desconto=51)


@pytest.mark.parametrize("campo", ["preco_unitario", "custo_unitario", "desconto"])
def test_valores_negativos_sao_recusados(produto, campo):
    valores = {"preco_unitario": 50, "custo_unitario": 20, "desconto": 0}
    valores[campo] = -1
    with pytest.raises(ValidacaoError):
        ItemPedido(produto, 1, **valores)


def test_opcao_de_outro_produto_e_recusada(produto):
    item = ItemPedido(produto, 1, 50, 20)
    with pytest.raises(ValidacaoError):
        item.adicionarOpcao(OpcaoPersonalizacao("Alheia", 1))


def test_opcao_inativa_e_recusada(produto):
    produto.opcoes[0].alternarAtivo()
    with pytest.raises(ValidacaoError):
        ItemPedido(produto, 1, 50, 20).adicionarOpcao(produto.opcoes[0])


def test_mesma_opcao_nao_entra_duas_vezes(produto):
    item = ItemPedido(produto, 1, 50, 20)
    item.adicionarOpcao(produto.opcoes[0])
    with pytest.raises(ValidacaoError):
        item.adicionarOpcao(produto.opcoes[0])


# PEDIDO: CRIAÇÃO
def test_pedido_novo(pedido):
    assert pedido.status is StatusPedido.SOLICITADO
    assert pedido.pagamento.status is StatusPagamento.AGUARDANDO_SINAL
    assert pedido.taxa_entrega == Decimal("0.00")
    assert pedido.valor_total == Decimal("0.00")
    assert pedido.itens == ()
    assert pedido.endereco is None


def test_entrega_exige_endereco(cliente):
    with pytest.raises(ValidacaoError):
        Pedido(cliente, TipoEntrega.ENTREGA, ENTREGA_OK, data_criacao=CRIACAO)


def test_entrega_com_endereco_do_cliente(cliente):
    pedido = Pedido(cliente, "entrega", ENTREGA_OK, endereco=cliente.enderecos[0], data_criacao=CRIACAO)
    assert pedido.endereco is cliente.enderecos[0]
    assert pedido.tipo_entrega is TipoEntrega.ENTREGA


def test_endereco_de_outro_cliente_e_recusado(cliente):
    outro = Cliente("João", "joao@email.com", "22988887777", None)
    alheio = Endereco("Rua B", "20", "Centro", "Campos", "28000-000")
    outro.adicionarEndereco(alheio)
    with pytest.raises(ValidacaoError):
        Pedido(cliente, TipoEntrega.ENTREGA, ENTREGA_OK, endereco=alheio, data_criacao=CRIACAO)


def test_tipo_de_entrega_invalido(cliente):
    with pytest.raises(ValidacaoError):
        Pedido(cliente, "drone", ENTREGA_OK, data_criacao=CRIACAO)


@pytest.mark.parametrize("data", ["2026-11-10", None, datetime(2026, 11, 2, 9, 0)])
def test_data_de_entrega_invalida(cliente, data):
    """Texto, None e uma data ANTERIOR à criação são recusados"""
    with pytest.raises(ValidacaoError):
        Pedido(cliente, TipoEntrega.RETIRADA, data, data_criacao=CRIACAO)


def test_pedido_sem_cliente():
    with pytest.raises(ValidacaoError):
        Pedido(None, TipoEntrega.RETIRADA, ENTREGA_OK, data_criacao=CRIACAO)


# PEDIDO: ITENS E VALORES
def test_valores_do_pedido(pedido_com_item):
    pedido_com_item.definirTaxaEntrega("8")
    assert pedido_com_item.subtotal_itens == Decimal("100.00")
    assert pedido_com_item.valor_total == Decimal("108.00")
    assert pedido_com_item.valor_sinal == Decimal("54.00")
    assert pedido_com_item.valor_restante == Decimal("54.00")
    assert pedido_com_item.valor_em_aberto == Decimal("108.00")


def test_adicionar_item_cria_vinculo(pedido, produto):
    pedido.atribuirID(9)
    item = ItemPedido(produto, 1, 50, 20)
    pedido.adicionarItem(item)
    assert pedido.itens == (item,)
    assert item.pedido is pedido
    assert item.pedido_id == 9


def test_item_nao_pode_ter_dois_pedidos(outro_pedido, pedido_com_item):
    with pytest.raises(ValidacaoError):
        outro_pedido.adicionarItem(pedido_com_item.itens[0])


def test_remover_item(pedido_com_item):
    item = pedido_com_item.itens[0]
    pedido_com_item.removerItem(item)
    assert pedido_com_item.itens == ()
    assert item.pedido is None


def test_remover_item_de_outro_pedido_falha(outro_pedido, pedido_com_item):
    with pytest.raises(ValidacaoError):
        outro_pedido.removerItem(pedido_com_item.itens[0])


def test_taxa_de_entrega_negativa_e_recusada(pedido):
    with pytest.raises(ValidacaoError):
        pedido.definirTaxaEntrega(-1)


# PEDIDO: FLUXO FELIZ
def test_fluxo_completo_ate_finalizar(pedido_com_item):
    p = pedido_com_item
    confirmar(p)
    assert p.status is StatusPedido.CONFIRMADO
    p.avancarStatus(StatusPedido.EM_PRODUCAO)
    p.avancarStatus(StatusPedido.PRONTO)
    p.avancarStatus(StatusPedido.ENTREGUE)
    p.registrarPagamentoRestante(FormaPagamento.DINHEIRO)
    assert p.valor_em_aberto == Decimal("0.00")
    p.avancarStatus(StatusPedido.FINALIZADO)
    assert p.status is StatusPedido.FINALIZADO


def test_avancar_aceita_status_como_texto(pedido_com_item):
    pedido_com_item.avancarStatus("orcamento")
    assert pedido_com_item.status is StatusPedido.ORCAMENTO


# PEDIDO: REGRAS DE NEGÓCIO
def test_orcamento_exige_itens(pedido):
    with pytest.raises(ValidacaoError):
        pedido.avancarStatus(StatusPedido.ORCAMENTO)
    assert pedido.status is StatusPedido.SOLICITADO


def test_prazo_minimo_do_produto_e_respeitado(cliente, produto):
    """Produto pede 48 h; entrega marcada para 24 h depois da criação é recusada e o status não muda"""
    pedido = Pedido(cliente, TipoEntrega.RETIRADA, datetime(2026, 11, 3, 10, 0), data_criacao=CRIACAO)
    pedido.adicionarItem(ItemPedido(produto, 1, 50, 20))
    with pytest.raises(ValidacaoError):
        pedido.avancarStatus(StatusPedido.ORCAMENTO)
    assert pedido.status is StatusPedido.SOLICITADO


def test_prazo_exatamente_no_limite_e_aceito(cliente, produto):
    pedido = Pedido(cliente, TipoEntrega.RETIRADA, datetime(2026, 11, 4, 10, 0), data_criacao=CRIACAO)
    pedido.adicionarItem(ItemPedido(produto, 1, 50, 20))
    pedido.avancarStatus(StatusPedido.ORCAMENTO)
    assert pedido.status is StatusPedido.ORCAMENTO


def test_prazo_usa_a_maior_antecedencia_entre_os_itens(cliente, produto):
    """Doce simples (24 h) + bolo (48 h): vale o maior prazo"""
    doce = Produto("Brigadeiro", 3, antecedencia_horas=24)
    pedido = Pedido(cliente, TipoEntrega.RETIRADA, datetime(2026, 11, 3, 12, 0), data_criacao=CRIACAO)
    pedido.adicionarItem(ItemPedido(doce, 10, 3, 1))
    pedido.validarPrazo()                               # só o doce: 24 h, passa
    pedido.adicionarItem(ItemPedido(produto, 1, 50, 20))
    with pytest.raises(ValidacaoError):
        pedido.validarPrazo()                           # com o bolo: 48 h, não passa


def test_sinal_so_depois_do_orcamento(pedido_com_item):
    with pytest.raises(ValidacaoError):
        pedido_com_item.registrarSinal(FormaPagamento.PIX)


def test_nao_confirma_sem_sinal(pedido_com_item):
    pedido_com_item.avancarStatus(StatusPedido.ORCAMENTO)
    with pytest.raises(ValidacaoError):
        pedido_com_item.avancarStatus(StatusPedido.CONFIRMADO)
    assert pedido_com_item.status is StatusPedido.ORCAMENTO


def test_pedido_confirmado_nao_pode_ser_alterado(pedido_com_item, produto):
    confirmar(pedido_com_item)
    with pytest.raises(ValidacaoError):
        pedido_com_item.adicionarItem(ItemPedido(produto, 1, 50, 20))
    with pytest.raises(ValidacaoError):
        pedido_com_item.removerItem(pedido_com_item.itens[0])
    with pytest.raises(ValidacaoError):
        pedido_com_item.definirTaxaEntrega(10)


def test_item_de_pedido_confirmado_fica_travado(pedido_com_item, produto):
    confirmar(pedido_com_item)
    with pytest.raises(ValidacaoError):
        pedido_com_item.itens[0].adicionarOpcao(produto.opcoes[0])


def test_transicao_proibida_e_recusada(pedido_com_item):
    """Solicitado -> Confirmado pula etapas: o autômato recusa"""
    with pytest.raises(TransicaoStatusError):
        pedido_com_item.avancarStatus(StatusPedido.CONFIRMADO)


def test_nao_cancela_antes_de_confirmar(pedido_com_item):
    with pytest.raises(TransicaoStatusError):
        pedido_com_item.avancarStatus(StatusPedido.CANCELADO, "desisti")


def test_cancelar_exige_motivo(pedido_com_item):
    confirmar(pedido_com_item)
    with pytest.raises(ValidacaoError):
        pedido_com_item.avancarStatus(StatusPedido.CANCELADO)
    with pytest.raises(ValidacaoError):
        pedido_com_item.avancarStatus(StatusPedido.CANCELADO, "   ")
    assert pedido_com_item.status is StatusPedido.CONFIRMADO


def test_cancelamento_guarda_motivo_e_nao_devolve_o_sinal(pedido_com_item):
    confirmar(pedido_com_item)
    pedido_com_item.avancarStatus(StatusPedido.CANCELADO, "Cliente desistiu")
    assert pedido_com_item.status is StatusPedido.CANCELADO
    assert pedido_com_item.motivo_cancelamento == "Cliente desistiu"
    assert pedido_com_item.pagamento.sinal_pago is True        # sem reembolso (entrevista 4.10)


def test_pedido_cancelado_e_final(pedido_com_item):
    confirmar(pedido_com_item)
    pedido_com_item.avancarStatus(StatusPedido.CANCELADO, "Cliente desistiu")
    with pytest.raises(TransicaoStatusError):
        pedido_com_item.avancarStatus(StatusPedido.EM_PRODUCAO)


def test_restante_so_depois_de_confirmado(pedido_com_item):
    pedido_com_item.avancarStatus(StatusPedido.ORCAMENTO)
    pedido_com_item.registrarSinal(FormaPagamento.PIX)
    with pytest.raises(ValidacaoError):
        pedido_com_item.registrarPagamentoRestante(FormaPagamento.PIX)


def test_nao_finaliza_sem_pagamento_integral(pedido_com_item):
    p = pedido_com_item
    confirmar(p)
    p.avancarStatus(StatusPedido.EM_PRODUCAO)
    p.avancarStatus(StatusPedido.PRONTO)
    p.avancarStatus(StatusPedido.ENTREGUE)
    with pytest.raises(ValidacaoError):
        p.avancarStatus(StatusPedido.FINALIZADO)
    assert p.status is StatusPedido.ENTREGUE


def test_rastreamento_pode_mudar_a_qualquer_momento(pedido_com_item):
    confirmar(pedido_com_item)
    pedido_com_item.alterarRastreamento("Motoboy João")
    assert pedido_com_item.rastreamento == "Motoboy João"