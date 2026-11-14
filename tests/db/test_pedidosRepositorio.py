"""
tests / db / test_pedidosRepositorio.py

RepositorioPedidos: montagem dos pedidos do seed (cliente, endereço, itens, opções, total),
listas da loja e do painel, gravação de pedido novo e atualização do pagamento
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.exceptions import ValidacaoError
from app.models import FormaPagamento, ItemPedido, Pedido, StatusPagamento, StatusPedido
from app.repositories.pedidos_rep import RepositorioPedidos
from app.repositories.produtos_rep import RepositorioProdutos
from app.repositories.usuarios_rep import RepositorioUsuarios


@pytest.fixture
def repo_pedidos(conexao, seed):
    """Repositório de pedidos com os repositórios de usuários e produtos na mesma conexão de teste"""
    return RepositorioPedidos(
        lambda: conexao,
        RepositorioUsuarios(lambda: conexao),
        RepositorioProdutos(lambda: conexao),
    )


# Leitura

def test_buscar_por_id_monta_o_pedido_completo(repo_pedidos):
    pedido = repo_pedidos.buscarPorId(1)

    assert pedido.status is StatusPedido.FINALIZADO
    assert pedido.cliente.id == 10
    assert pedido.endereco.id == 1
    assert len(pedido.itens) == 1
    assert pedido.itens[0].opcoes[0].opcao.nome == "Escrita personalizada"
    # 98 do bolo + 10 da escrita + 8 de taxa
    assert pedido.valor_total == Decimal("116.00")


def test_opcao_com_quantidade_cobra_por_unidade(repo_pedidos):
    # 78 + 10 × 3,00 + 10 de taxa (depende da correção do seed da Tarefa 0.5)
    assert repo_pedidos.buscarPorId(3).valor_total == Decimal("118.00")


def test_pedido_com_dois_itens(repo_pedidos):
    # 135 + 10 × 3,50
    pedido = repo_pedidos.buscarPorId(7)

    assert len(pedido.itens) == 2
    assert pedido.valor_total == Decimal("170.00")


def test_pedido_de_retirada_vem_sem_endereco(repo_pedidos):
    assert repo_pedidos.buscarPorId(2).endereco is None


def test_buscar_por_id_inexistente_devolve_none(repo_pedidos):
    assert repo_pedidos.buscarPorId(999) is None


def test_item_de_pedido_confirmado_vem_travado(repo_pedidos):
    pedido = repo_pedidos.buscarPorId(5)
    item = pedido.itens[0]
    opcao = item.produto.opcoes[0]

    with pytest.raises(ValidacaoError):
        item.adicionarOpcao(opcao)


def test_listar_do_cliente_vem_do_mais_recente_para_o_mais_antigo(repo_pedidos):
    assert [pedido.id for pedido in repo_pedidos.listarDoCliente(10)] == [5, 1]


def test_listar_por_status(repo_pedidos):
    assert [pedido.id for pedido in repo_pedidos.listar(status="cancelado")] == [8]


def test_listar_com_busca_sem_resultado(repo_pedidos):
    assert repo_pedidos.listar(busca="zzz") == []


# Gravação

def test_salvar_novo_grava_pedido_e_itens(repo_pedidos):
    cliente = repo_pedidos._repo_usuarios.buscarPorId(10)
    produto = repo_pedidos._repo_produtos.buscarPorId(18)
    pedido = Pedido(
        cliente=cliente,
        tipo_entrega="retirada",
        data_entrega_ou_retirada=datetime.now() + timedelta(days=3),
    )
    pedido.adicionarItem(
        ItemPedido(produto, 10, preco_unitario=Decimal("3.50"), custo_unitario=Decimal("1.60"))
    )

    repo_pedidos.salvarNovo(pedido)

    assert pedido.id is not None
    assert repo_pedidos.buscarPorId(pedido.id).valor_total == Decimal("35.00")


def test_atualizar_grava_o_pagamento(repo_pedidos):
    pedido = repo_pedidos.buscarPorId(6)
    pedido.registrarSinal(FormaPagamento.PIX)

    repo_pedidos.atualizar(pedido)

    assert repo_pedidos.buscarPorId(6).pagamento.status is StatusPagamento.SINAL_PAGO
