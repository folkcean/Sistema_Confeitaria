"""
tests / rotas / test_painel_pedidos.py

controllers/painel.py, pedidos: lista com filtros, detalhe, mudança de status (com a baixa de
estoque na confirmação), registro de pagamento e cancelamento
"""

from decimal import Decimal

import pytest

from app.models import FormaPagamento, StatusPagamento, StatusPedido
from app.repositories.pedidos_rep import RepositorioPedidos
from app.repositories.produtos_rep import RepositorioProdutos
from app.repositories.usuarios_rep import RepositorioUsuarios


@pytest.fixture
def pedidos_no_banco(conexao, seed):
    """Repositório de pedidos para conferir no banco o que as rotas gravaram"""
    return RepositorioPedidos(
        lambda: conexao, RepositorioUsuarios(lambda: conexao), RepositorioProdutos(lambda: conexao)
    )


def consultar(conexao, sql, parametros=()):
    """Primeira coluna da primeira linha de uma consulta (a conexão de teste devolve tuplas)"""
    with conexao.cursor() as cursor:
        cursor.execute(sql, parametros)
        return cursor.fetchone()[0]


def ids(templates):
    """Ids dos pedidos que a última página renderizada recebeu, na ordem"""
    return [pedido.id for pedido in templates[-1][1]["pedidos"]]


# ---------------------------------------------------------------- Lista

def test_lista_traz_todos_do_mais_recente_para_o_mais_antigo(navegador, como_funcionario, templates):
    resposta = navegador.get("/painel/pedidos")

    assert resposta.status_code == 200
    pedidos = templates[-1][1]["pedidos"]
    assert len(pedidos) == 8
    datas = [pedido.data_entrega_ou_retirada for pedido in pedidos]
    assert datas == sorted(datas, reverse=True)


def test_filtro_por_status(navegador, como_funcionario, templates):
    navegador.get("/painel/pedidos?status=pronto")
    assert ids(templates) == [3]


def test_busca_pelo_nome_do_cliente(navegador, como_funcionario, templates):
    navegador.get("/painel/pedidos?q=Ana")
    assert ids(templates) == [5, 1]


def test_data_invalida_avisa_e_lista_sem_o_filtro(navegador, como_funcionario, templates, mensagens):
    navegador.get("/painel/pedidos?data=abc")

    assert mensagens[-1][0] == "erro"
    assert len(ids(templates)) == 8


# ---------------------------------------------------------------- Detalhe

def test_detalhe_mostra_os_proximos_status_e_esconde_o_cpf_do_funcionario(navegador, como_funcionario, templates):
    navegador.get("/painel/pedidos/6")
    variaveis = templates[-1][1]

    assert variaveis["proximos_status"] == ["confirmado"]
    assert "cpf" not in variaveis["cliente_dados"]


# ---------------------------------------------------------------- Status

def test_solicitado_vai_para_orcamento(navegador, como_funcionario, pedidos_no_banco):
    navegador.post("/painel/pedidos/7/status", data={"novo_status": "orcamento"})
    assert pedidos_no_banco.buscarPorId(7).status is StatusPedido.ORCAMENTO


def test_confirmar_sem_sinal_e_recusado(navegador, como_funcionario, mensagens, pedidos_no_banco):
    navegador.post("/painel/pedidos/6/status", data={"novo_status": "confirmado"})

    assert "sinal de 50%" in mensagens[-1][1]
    assert pedidos_no_banco.buscarPorId(6).status is StatusPedido.ORCAMENTO


# ---------------------------------------------------------------- Pagamento e confirmação

def test_funcionario_nao_registra_pagamento(navegador, como_funcionario):
    resposta = navegador.post("/painel/pedidos/6/pagamento",
                              data={"status_pagamento": "sinal_pago", "forma_pagamento": "pix"})
    assert resposta.status_code == 403


def test_sinal_e_confirmacao_com_baixa_no_estoque(navegador, como_admin, pedidos_no_banco, conexao):
    navegador.post("/painel/pedidos/6/pagamento", data={"status_pagamento": "sinal_pago", "forma_pagamento": "pix"})

    pagamento = pedidos_no_banco.buscarPorId(6).pagamento
    assert pagamento.status is StatusPagamento.SINAL_PAGO
    assert pagamento.forma_sinal is FormaPagamento.PIX

    navegador.post("/painel/pedidos/6/status", data={"novo_status": "confirmado"})

    assert pedidos_no_banco.buscarPorId(6).status is StatusPedido.CONFIRMADO
    consumos = consultar(
        conexao, "SELECT count(*) FROM movimentacao_estoque WHERE id_pedido = 6 AND tipo = 'consumo'"
    )
    assert consumos > 0
    # 1 bolo do produto 1 = 1,5 × receita 8, que usa 2 latas: 1,5 × 2 = 3
    leite_condensado = consultar(conexao, "SELECT quantidade_atual FROM insumo WHERE id_insumo = 4")
    assert leite_condensado == Decimal("21")


# ---------------------------------------------------------------- Cancelamento

def test_cancelar_sem_motivo_e_recusado(navegador, como_admin, mensagens):
    resposta = navegador.post("/painel/pedidos/5/cancelar", data={"motivo_cancelamento": ""})

    assert resposta.status_code == 400
    assert mensagens[-1][0] == "erro"


def test_cancelar_com_motivo(navegador, como_admin, pedidos_no_banco):
    navegador.post("/painel/pedidos/5/cancelar", data={"motivo_cancelamento": "Cliente desistiu"})

    pedido = pedidos_no_banco.buscarPorId(5)
    assert pedido.status is StatusPedido.CANCELADO
    assert pedido.motivo_cancelamento == "Cliente desistiu"


def test_pedido_solicitado_nao_cancela(navegador, como_admin, mensagens, pedidos_no_banco):
    navegador.post("/painel/pedidos/7/cancelar", data={"motivo_cancelamento": "Cliente desistiu"})

    assert mensagens[-1][0] == "erro"
    assert pedidos_no_banco.buscarPorId(7).status is StatusPedido.SOLICITADO
