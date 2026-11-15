"""
app / services / compra_insumo_service.py

Casos de uso das compras de insumos:
    - registrar uma compra nova de um fornecedor ativo, com os itens
    - receber a compra: entrada no estoque + custo do insumo atualizado + gravação, tudo junto
    - cancelar uma compra pendente
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Protocol

from app.exceptions import ValidacaoError
from app.models.compra_insumo import CompraInsumo
from app.models.estoque import Estoque
from app.models.fornecedor import Fornecedor
from app.models.insumo import Insumo
from app.models.item_compra_insumo import ItemCompraInsumo
from app.models.movimentacao_estoque import MovimentacaoEstoque
from app.validators.campos import garantir


class RepositorioEstoque(Protocol):
    """
    Contrato da parte do repositório de insumos que o recebimento usa (o RepositorioInsumos já cumpre)
    """

    def registrarMovimentacao(self, insumo: Insumo, movimentacao: MovimentacaoEstoque):
        """Grava o saldo novo do insumo e a movimentação, juntos"""
        ...

    def salvar(self, insumo: Insumo):
        """Grava o cadastro do insumo (inclusive custo_por_unidade)"""
        ...


class RepositorioCompras(Protocol):
    """
    Contrato que o repositório de compras (camada de banco) precisa cumprir
    """

    def salvarNova(self, compra: CompraInsumo) -> CompraInsumo:
        """INSERT da compra e dos itens numa transação; atribui os ids gerados"""
        ...

    def atualizar(self, compra: CompraInsumo) -> CompraInsumo:
        """UPDATE do que muda depois de criada: status e data_entrega"""
        ...

    def gravarRecebimento(self, compra: CompraInsumo, movimentacoes: list[MovimentacaoEstoque],
                          repo_estoque: RepositorioEstoque) -> None:
        """
        Numa transação só: atualizar(compra), repo_estoque.registrarMovimentacao de cada movimentação
        e repo_estoque.salvar de cada insumo da compra (custo novo). Se algo falhar, nada fica gravado
        """
        ...


class ServicoCompras:
    """
    Registra, recebe e cancela compras de insumos
    """

    def __init__(self, repo_compras: RepositorioCompras, repo_estoque: RepositorioEstoque):
        """Recebe os repositórios prontos (injeção de dependência): nos testes, entram objetos falsos"""
        self._repo_compras = repo_compras
        self._repo_estoque = repo_estoque

    def registrarCompra(
            self,
            fornecedor: Fornecedor,
            linhas: Iterable[tuple[Insumo, object, object]],
            data_entrega=None,
            nota_fiscal: str | None = None
    ) -> CompraInsumo:
        """
        Cria e grava uma compra pendente

        `linhas`: pares (insumo, quantidade, custo_unitario), na unidade de COMPRA do insumo
        O fornecedor precisa estar ativo. Essa regra fica aqui, e não no construtor da CompraInsumo,
        porque o construtor também remonta compras antigas, de fornecedores que já foram desativados
        """
        garantir(
            fornecedor.ativo,
            ValidacaoError(f"O fornecedor {fornecedor.nome!r} está desativado"),
        )
        compra = CompraInsumo(fornecedor, data_entrega=data_entrega, nota_fiscal=nota_fiscal)
        # Cada adicionarItem confere insumo ativo e insumo repetido
        for insumo, quantidade, custo_unitario in linhas:
            compra.adicionarItem(ItemCompraInsumo(insumo, quantidade, custo_unitario))
        garantir(compra.itens, ValidacaoError("Informe pelo menos um item da compra"))

        self._repo_compras.salvarNova(compra)
        return compra

    def receberCompra(self, compra: CompraInsumo, estoque: Estoque, data=None) -> list[MovimentacaoEstoque]:
        """
        A mercadoria chegou: dá entrada no estoque, atualiza o custo dos insumos e grava tudo junto
        (entrevista 8.5: "o estoque deve ser atualizado automaticamente")

        Ordem: 1) a compra confere e muda o status, 2) o estoque confere todos os itens e dá entrada,
        3) os custos mudam, 4) o repositório grava tudo numa transação. Se 1 ou 2 falharem, nada mudou
        no estoque e nada foi gravado: o objeto da compra é descartado junto com a requisição
        """
        compra.receber(data)
        # O Estoque confere que cada insumo é dele (`is`) e só então soma: tudo ou nada
        movimentacoes = estoque.receber(compra.entradas(), id_compra=compra.id)
        self._atualizarCustos(compra)
        self._repo_compras.gravarRecebimento(compra, movimentacoes, self._repo_estoque)
        return movimentacoes

    def cancelarCompra(self, compra: CompraInsumo) -> CompraInsumo:
        """Cancela uma compra pendente. Nada entra no estoque"""
        compra.cancelar()
        self._repo_compras.atualizar(compra)
        return compra

    @staticmethod
    def _atualizarCustos(compra: CompraInsumo) -> None:
        """
        O custo do insumo passa a ser o da última compra (entrevista 8.6: o preço de compra entra no custo
        dos produtos). Item com custo zero (brinde, bonificação) não mexe no custo cadastrado
        """
        # filter mantém só os itens com custo > 0
        for item in filter(lambda item: item.custo_unitario > Decimal("0"), compra.itens):
            item.insumo.alterarCustoPorUnidade(item.custo_unitario)
