"""
app / services / baixa_estoque.py

BAIXA DE ESTOQUE DO PEDIDO (s5)

Quando um pedido é CONFIRMADO, os insumos que ele usa saem do estoque:
    pedido -> itens -> produto -> receitas -> insumos (já convertidos para a unidade do estoque)

REGRA "TUDO OU NADA": se faltar QUALQUER insumo, nada é descontado e o erro (PedidoSemEstoqueError) explica
exatamente o que falta. Isso é garantido por Estoque.consumir (semana 3); aqui só monta a lista de necessidades
"""
from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from app.exceptions import PedidoSemEstoqueError
from app.models.estoque import Estoque
from app.models.insumo import Insumo
from app.models.movimentacao_estoque import MovimentacaoEstoque
from app.models.pedido import Pedido
from app.validators.campos import garantir


class BaixaEstoque:
    """
    Calcula e executa o desconto dos insumos de um pedido
    """

    def __init__(self, estoque: Estoque,
                 gravar_movimentacao: Callable[[Insumo, MovimentacaoEstoque], None] | None = None):
        """`gravar_movimentacao(insumo, movimentacao)` é chamada UMA vez por insumo descontado (para gravar no banco)

        `a or b`: se nenhuma função foi informada, usa `self._naoGravar`, que não faz nada.
        """
        self._estoque = estoque
        self._gravar_movimentacao = gravar_movimentacao or self._naoGravar

    @staticmethod
    def _naoGravar(insumo: Insumo, movimentacao: MovimentacaoEstoque) -> None:
        """Gravação "vazia" usada quando não há banco (testes). `pass` = não faz nada"""
        pass

    def necessidadesDoPedido(self, pedido: Pedido) -> list[tuple[Insumo, Decimal]]:
        """Todos os insumos que o pedido consome, no formato (insumo, quantidade na unidade da receita)

        Para cada item, pede ao produto quanto precisa para a QUANTIDADE daquele item. O mesmo insumo pode
        aparecer várias vezes: o Estoque soma por insumo antes de conferir o saldo
        """
        necessidades: list[tuple[Insumo, Decimal]] = []
        for item in pedido.itens:
            necessidades.extend(item.produto.necessidades(item.quantidade))
        return necessidades

    def verificar(self, pedido: Pedido) -> list[dict]:
        """O que FALTARIA para atender ao pedido, sem alterar nada. Lista vazia = tem tudo"""
        return self._estoque.verificarDisponibilidade(self.necessidadesDoPedido(pedido))

    def executar(self, pedido: Pedido) -> list[MovimentacaoEstoque]:
        """Desconta os insumos do pedido (tudo ou nada) e grava cada movimentação

        LÓGICA:
        1) lista de faltas; se houver alguma, levanta PedidoSemEstoqueError (nada foi alterado)
        2) consome no estoque (ligando cada consumo ao id do pedido)
        3) grava cada movimentação (se houver banco). Quem chama deve usar uma transação para que, se a gravação falhar no meio, o banco desfaça tudo
        """
        faltas = self.verificar(pedido)
        garantir(not faltas, PedidoSemEstoqueError(faltas))
        movimentacoes = self._estoque.consumir(self.necessidadesDoPedido(pedido), id_pedido=pedido.id)
        for movimentacao in movimentacoes:
            self._gravar_movimentacao(movimentacao.insumo, movimentacao)
        return movimentacoes