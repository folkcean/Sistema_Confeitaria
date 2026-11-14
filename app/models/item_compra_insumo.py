"""
app / models / item_compra_insumo.py

Tabela ITEM_COMPRA_INSUMO no DER: uma linha da compra (qual insumo, quanto e a que preço)

A quantidade e o custo estão na UNIDADE DE COMPRA do insumo (a unidade_medida: kg, lata, dúzia...),
que é a mesma unidade em que o Estoque.receber() dá entrada
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING

from app.exceptions import ValidacaoError
from app.validators.campos import Validador, garantir
from .base import Entidade

# Só para as dicas de tipo (evita import circular: a compra importa o item)
if TYPE_CHECKING:
    from .compra_insumo import CompraInsumo
    from .insumo import Insumo


class ItemCompraInsumo(Entidade):
    """
    DER: ID_item_compra, FK do insumo, FK da compra, quantidade numeric(10,3), custo_unitario numeric(10,4)
    """

    _CENTAVOS = Decimal("0.01")

    def __init__(self, insumo: Insumo, quantidade, custo_unitario, id_item_compra: int | None = None):
        """Valida tudo na criação. A compra dona é definida depois, por CompraInsumo.adicionarItem()"""
        super().__init__(id_item_compra)
        garantir(insumo is not None, ValidacaoError("O item da compra precisa de um insumo"))
        self._insumo = insumo
        self._quantidade = Validador.quantidadePositiva(quantidade, "quantidade comprada")
        # 4 casas (numeric(10,4)): o custo de uma unidade pode ter fração de centavo. 0 é aceito (brinde)
        self._custo_unitario = Validador.custoUnitario(custo_unitario, "custo unitário")
        # Compra dona (None até a CompraInsumo.adicionarItem)
        self._compra: CompraInsumo | None = None

    @property
    def insumo(self) -> Insumo:
        return self._insumo

    @property
    def quantidade(self) -> Decimal:
        return self._quantidade

    @property
    def custo_unitario(self) -> Decimal:
        return self._custo_unitario

    @property
    def compra(self) -> CompraInsumo | None:
        return self._compra

    @property
    def insumo_id(self) -> int | None:
        """Valor da FK do insumo"""
        return self._insumo.id

    @property
    def compra_id(self) -> int | None:
        """Valor da FK da compra (None enquanto o item não pertence a uma compra gravada)"""
        # `a and a.id`: sem compra, devolve None sem tentar ler .id de None
        return self._compra and self._compra.id

    @property
    def subtotal(self) -> Decimal:
        """Quantidade x custo unitário, em reais (2 casas)"""
        return (self._quantidade * self._custo_unitario).quantize(self._CENTAVOS, rounding=ROUND_HALF_UP)

    def _vincular(self, compra: CompraInsumo | None) -> None:
        """Define (ou desfaz, com None) a compra dona. Chamado só pela CompraInsumo"""
        self._compra = compra

    def __repr__(self) -> str:
        """Texto exibido ao imprimir o objeto"""
        return f"<ItemCompraInsumo id={self.id} {self._quantidade} {self._insumo.unidade_medida} de {self._insumo.nome!r}>"
