"""
app / models / compra_insumo.py

Tabela COMPRA_INSUMO no DER: uma compra feita a um fornecedor, com um ou mais itens
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from app.exceptions import ValidacaoError
from app.validators.campos import Validador, garantir
from .base import Entidade
from .enums import StatusCompra
from .item_compra_insumo import ItemCompraInsumo

# Só para as dicas de tipo
if TYPE_CHECKING:
    from .fornecedor import Fornecedor
    from .insumo import Insumo

_ZERO = Decimal("0.00")


class CompraInsumo(Entidade):
    """
    DER: ID_compra_insumo, FK do fornecedor, data_compra (default now), data_entrega (nula),
    valor_total numeric(10,2), status, nota_fiscal (nula)

    valor_total não é guardado no objeto: é calculado pelos itens (o repositório grava o valor calculado)
    """

    # Como transformar cada tipo aceito em datetime (o banco guarda timestamp; o formulário manda só a data)
    # A busca é pelo tipo exato, type(valor): por isso datetime e date são chaves separadas
    _PARA_DATA_HORA = {
        datetime: lambda valor, campo: valor,
        date: lambda valor, campo: datetime.combine(valor, time()),
        str: lambda valor, campo: datetime.combine(Validador.data(valor, campo), time()),
    }

    def __init__(
            self,
            fornecedor: Fornecedor,
            data_entrega=None,
            nota_fiscal: str | None = None,
            status: StatusCompra = StatusCompra.PENDENTE,
            data_compra: datetime | None = None,
            id_compra_insumo: int | None = None
    ):
        """
        Valida e normaliza. `data_compra` pode ser informada (recarga do banco e testes); senão é agora
        `data_entrega` aceita datetime, date ou texto AAAA-MM-DD; vazio = sem previsão
        """
        super().__init__(id_compra_insumo)
        garantir(fornecedor is not None, ValidacaoError("A compra precisa de um fornecedor"))
        self._fornecedor = fornecedor
        # `a or b`: se data_compra foi informada usa ela; senão usa o momento atual
        self._data_compra = data_compra or datetime.now()
        self._data_entrega = self._dataEntrega(data_entrega)
        self._nota_fiscal = Validador.textoOpcional(nota_fiscal, "nota fiscal")
        # Aceita StatusCompra.RECEBIDA ou o texto "recebida" (vindo do banco)
        self._status = Validador.opcaoDe(StatusCompra, status, "status da compra")
        self._itens: list[ItemCompraInsumo] = []

    def _dataEntrega(self, valor) -> datetime | None:
        """
        Converte a data de entrega para datetime e confere que não é antes do dia da compra
        Vazio ou None vira None (coluna anulável)
        """
        data = Validador.opcional(self._paraDataHora, valor, "data de entrega")
        # `data is None or ...`: sem data não há o que comparar, e o `or` nem chega a ler data.date()
        garantir(
            data is None or data.date() >= self._data_compra.date(),
            ValidacaoError("A data de entrega não pode ser antes da data da compra"),
        )
        return data

    @classmethod
    def _paraDataHora(cls, valor, campo: str) -> datetime:
        """Escolhe o conversor pelo tipo exato do valor; tipo desconhecido é erro"""
        conversor = cls._PARA_DATA_HORA.get(type(valor))
        garantir(conversor, ValidacaoError(f"O campo '{campo}' deve ser uma data válida"))
        return conversor(valor, campo)

    # Leitura dos campos
    @property
    def fornecedor(self) -> Fornecedor:
        return self._fornecedor

    @property
    def fornecedor_id(self) -> int | None:
        """Valor da FK do fornecedor"""
        return self._fornecedor.id

    @property
    def data_compra(self) -> datetime:
        return self._data_compra

    @property
    def data_entrega(self) -> datetime | None:
        """Antes de receber: a previsão. Depois de receber: quando a mercadoria chegou"""
        return self._data_entrega

    @property
    def nota_fiscal(self) -> str | None:
        return self._nota_fiscal

    @property
    def status(self) -> StatusCompra:
        return self._status

    @property
    def itens(self) -> tuple[ItemCompraInsumo, ...]:
        """Cópia imutável dos itens. Para alterar, use adicionarItem/removerItem"""
        return tuple(self._itens)

    @property
    def valor_total(self) -> Decimal:
        """Soma dos subtotais dos itens (cada um já em reais), o mesmo valor que a tela mostra linha a linha"""
        return sum((item.subtotal for item in self._itens), _ZERO)

    # Itens
    def _exigirPendente(self) -> None:
        """Garante que a compra ainda pode mudar. Recebida e cancelada são finais"""
        garantir(
            self._status is StatusCompra.PENDENTE,
            ValidacaoError(f"Uma compra '{self._status.value}' não pode mais ser alterada"),
        )

    def adicionarItem(self, item: ItemCompraInsumo) -> None:
        """
        Inclui um item na compra pendente. O item não pode já ser de outra compra, o insumo precisa estar
        ativo e não pode aparecer duas vezes (some as quantidades numa linha só)
        """
        self._exigirPendente()
        garantir(item.compra is None, ValidacaoError("Este item já pertence a uma compra"))
        garantir(item.insumo.ativo, ValidacaoError(f"O insumo {item.insumo.nome!r} está desativado"))
        # any(...) = "existe algum": `is` compara o objeto, como o Estoque faz com os insumos
        garantir(
            not any(existente.insumo is item.insumo for existente in self._itens),
            ValidacaoError(f"O insumo {item.insumo.nome!r} já está nesta compra"),
        )
        item._vincular(self)
        self._itens.append(item)

    def removerItem(self, item: ItemCompraInsumo) -> None:
        """Tira um item da compra pendente e desfaz o vínculo"""
        self._exigirPendente()
        garantir(item in self._itens, ValidacaoError("Este item não faz parte desta compra"))
        self._itens.remove(item)
        item._vincular(None)

    def _carregarItem(self, item: ItemCompraInsumo) -> None:
        """
        Uso interno do repositório: monta a compra lida do banco sem refazer as regras
        (uma compra recebida tem itens, e um insumo pode ter sido desativado depois)
        """
        item._vincular(self)
        self._itens.append(item)

    # Mudança de status
    def receber(self, data: datetime | None = None) -> None:
        """
        Marca a compra como recebida. A data de entrega passa a ser a da chegada (ou a informada)

        Só confere e muda a compra: a entrada no estoque é do ServicoCompras, com entradas()
        A compra precisa estar gravada, porque as movimentações de entrada guardam o id dela
        """
        self._exigirPendente()
        garantir(self._itens, ValidacaoError("Uma compra sem itens não pode ser recebida"))
        garantir(self.id is not None, ValidacaoError("Grave a compra antes de recebê-la"))
        self._data_entrega = self._dataEntrega(data or datetime.now())
        self._status = StatusCompra.RECEBIDA

    def cancelar(self) -> None:
        """Cancela a compra pendente. Compra recebida não cancela: o estoque já recebeu a entrada"""
        self._exigirPendente()
        self._status = StatusCompra.CANCELADA

    def entradas(self) -> list[tuple[Insumo, Decimal]]:
        """
        Pares (insumo, quantidade na unidade de compra), no formato que o Estoque.receber() espera
        """
        return [(item.insumo, item.quantidade) for item in self._itens]

    def __repr__(self) -> str:
        """Texto exibido ao imprimir o objeto"""
        return (f"<CompraInsumo id={self.id} de {self._fornecedor.nome!r} "
                f"R$ {self.valor_total} ({self._status.value}, {len(self._itens)} itens)>")
