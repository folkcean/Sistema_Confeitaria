"""
tests / rotas / test_loja_pedidos.py

controllers/loja.py, pedidos: envio do carrinho, lista dos pedidos do cliente e acompanhamento
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models import FormaPagamento, StatusPagamento, StatusPedido
from app.repositories.pedidos_rep import RepositorioPedidos
from app.repositories.produtos_rep import RepositorioProdutos
from app.repositories.usuarios_rep import RepositorioUsuarios
from app.services.carrinho import Carrinho


@pytest.fixture
def pedidos_no_banco(conexao, seed):
    """Repositório de pedidos para conferir no banco o que a rota gravou"""
    return RepositorioPedidos(
        lambda: conexao, RepositorioUsuarios(lambda: conexao), RepositorioProdutos(lambda: conexao)
    )


def daqui_a(**tempo):
    """Data no formato do <input type="datetime-local"> (AAAA-MM-DDTHH:MM)"""
    return (datetime.now() + timedelta(**tempo)).strftime("%Y-%m-%dT%H:%M")


def por_no_carrinho(navegador, produto_id, quantidade, opcoes=None):
    """POST de verdade em /loja/carrinho/adicionar. `opcoes` = {id_opcao: quantidade}"""
    opcoes = opcoes or {}
    dados = {"produto_id": produto_id, "quantidade": quantidade, "opcoes": list(opcoes)}
    for id_opcao, quantidade_opcao in opcoes.items():
        dados[f"qtd_opcao_{id_opcao}"] = quantidade_opcao
    navegador.post("/loja/carrinho/adicionar", data=dados)


def enviar(navegador, **trocas):
    """Envio de retirada para daqui a 3 dias, com sinal no pix; `trocas` muda algum campo"""
    dados = {
        "tipo_entrega": "retirada",
        "data_entrega_ou_retirada": daqui_a(days=3),
        "nome_recebedor": "Ana",
        "forma_pagamento_sinal": "pix",
        "observacoes": "",
    }
    return navegador.post("/loja/carrinho/enviar", data=dados | trocas)


def maior_id_de_pedido(conexao):
    """O maior id_pedido no banco (para saber se um pedido novo foi gravado)"""
    with conexao.cursor() as cursor:
        cursor.execute("SELECT max(id_pedido) FROM pedido")
        # A conexão de teste devolve tuplas: [0] é a primeira coluna
        return cursor.fetchone()[0]


# Envio

def test_enviar_grava_o_pedido_e_esvazia_o_carrinho(navegador, como_cliente, pedidos_no_banco):
    por_no_carrinho(navegador, 18, 10)

    resposta = enviar(navegador)

    assert resposta.status_code == 302
    id_pedido = int(resposta.headers["Location"].rstrip("/").split("/")[-1])
    assert resposta.headers["Location"].endswith(f"/loja/pedidos/{id_pedido}")

    pedido = pedidos_no_banco.buscarPorId(id_pedido)
    assert pedido.status is StatusPedido.SOLICITADO
    assert pedido.valor_total == Decimal("35.00")
    assert pedido.pagamento.forma_sinal is FormaPagamento.PIX
    assert pedido.pagamento.status is StatusPagamento.AGUARDANDO_SINAL

    with navegador.session_transaction() as sessao:
        assert Carrinho(sessao).linhas == []


def test_opcao_e_multiplicada_pela_quantidade_do_produto(navegador, como_cliente, pedidos_no_banco):
    # 2 bolos com escrita (R$ 10,00 por bolo)
    por_no_carrinho(navegador, 1, 2, opcoes={4: 1})

    resposta = enviar(navegador)
    id_pedido = int(resposta.headers["Location"].rstrip("/").split("/")[-1])

    pedido = pedidos_no_banco.buscarPorId(id_pedido)
    # 2 × 98 + 2 × 10
    assert pedido.valor_total == Decimal("216.00")
    assert pedido.itens[0].opcoes[0].quantidade == 2


def test_prazo_insuficiente_nao_grava_nada(navegador, como_cliente, mensagens, conexao):
    por_no_carrinho(navegador, 1, 1)
    antes = maior_id_de_pedido(conexao)

    enviar(navegador, data_entrega_ou_retirada=daqui_a(hours=2))

    assert "Prazo insuficiente" in mensagens[-1][1]
    assert maior_id_de_pedido(conexao) == antes


def test_entrega_sem_endereco(navegador, como_cliente, mensagens):
    por_no_carrinho(navegador, 18, 10)

    enviar(navegador, tipo_entrega="entrega")

    assert mensagens[-1] == ("erro", "Pedidos para entrega precisam de um endereço")


def test_carrinho_vazio(navegador, como_cliente, mensagens):
    resposta = enviar(navegador)

    assert resposta.status_code == 302
    assert mensagens[-1] == ("erro", "Seu carrinho está vazio.")


# Lista e acompanhamento

def test_lista_traz_os_pedidos_do_cliente_do_mais_recente_para_o_mais_antigo(navegador, como_cliente, templates):
    navegador.get("/loja/pedidos")

    assert [pedido.id for pedido in templates[-1][1]["pedidos"]] == [5, 1]


def test_acompanhar_pedido_mostra_os_valores(navegador, como_cliente, templates):
    resposta = navegador.get("/loja/pedidos/1")

    assert resposta.status_code == 200
    assert templates[-1][1]["valores"]["total"] == Decimal("116.00")


def test_pedido_de_outro_cliente_da_404(navegador, como_cliente):
    # O pedido 2 é do cliente 11
    assert navegador.get("/loja/pedidos/2").status_code == 404
