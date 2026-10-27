"""
app / models / movimentacao_estoque.py

Tabela MOVIMENTACAO_ESTOQUE no DER

É o registro de cada mudança no saldo de um insumo: entrou/foi consumido/perdeu, foi ajustado

Depois de criado é imutável -> mantém o histórico confiável. 
É permitido desfazer um ajuste manual: em vez de apagar o registro atual, cria outro que compensa

Ligações no DER:
    insumo - FK obrigatória (de qual item é a movimentação)
    pedido - FK opcional (em caso de consumo)
    compra - FK opcional (em caso de entrada)
obs: as classes Pedido e Compra ainda não foram implementadas
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
 
from app.exceptions import ValidacaoError
from app.validators.campos import Validador, garantir
 
from .base import Entidade
from .enums import TipoMovimentacao
 
# Só para as dicas de tipo 
if TYPE_CHECKING:
    from .insumo import Insumo

class MovimentacaoEstoque(Entidade):
    """
    DER: ID_movimentacao, FK do insumo, tipo, quantidade numeric(10,3), data,
    motivo (nulo), FK do pedido (nula), FK da compra (nula)
    """
 
    def __init__(
        self, 
        insumo: Insumo, 
        tipo: TipoMovimentacao, 
        quantidade, 
        motivo: str = "",
        id_pedido: int | None = None, 
        id_compra: int | None = None,
        data: datetime | None = None, 
        id_movimentacao: int | None = None
    ):
        
        """
        Valida tudo no momento da criação 
        Normalmente quem cria é o próprio Insumo
        """
        super().__init__(id_movimentacao)
        self._insumo = insumo
        # Aceita TipoMovimentacao.ENTRADA ou o texto "entrada" (vindo do banco)
        self._tipo = Validador.opcaoDe(TipoMovimentacao, tipo, "tipo")
        # Cada tipo valida a quantidade do seu jeito (ajuste aceita negativo, os outros só aceitam positivo)
        self._quantidade = self._tipo.validarQuantidade(quantidade)
        self._motivo = Validador.textoOpcional(motivo, "motivo")
        # `a or b`: se houver motivo (verdadeiro), passa; se não houver, só passa quando o tipo NÃO exige motivo
        garantir(
            self._motivo or not self._tipo.exigeMotivo(),
            ValidacaoError(f"Movimentações do tipo '{self._tipo.value}' exigem um motivo"),
        )
        # opcionalSeInformado: None continua None; qualquer outro valor precisa ser um inteiro >= 1
        self._id_pedido = Validador.opcionalSeInformado(Validador.inteiroPositivo, id_pedido, "pedido")
        self._id_compra = Validador.opcionalSeInformado(Validador.inteiroPositivo, id_compra, "compra")
        # DER: pedido só em consumo; compra só em entrada
        garantir(
            self._id_pedido is None or self._tipo is TipoMovimentacao.CONSUMO,
            ValidacaoError("Somente um consumo pode estar ligado a um pedido"),
        )
        garantir(
            self._id_compra is None or self._tipo is TipoMovimentacao.ENTRADA,
            ValidacaoError("Somente uma entrada pode estar ligada a uma compra"),
        )
        self._data = data or datetime.now()
 
    # Leitura
    @property
    def insumo(self) -> Insumo: 
        return self._insumo
    @property
    def tipo(self) -> TipoMovimentacao: 
        return self._tipo
    @property
    def quantidade(self) -> Decimal: 
        return self._quantidade
    @property
    def motivo(self) -> str | None: 
        return self._motivo
    @property
    def id_pedido(self) -> int | None: 
        return self._id_pedido
    @property
    def id_compra(self) -> int | None: 
        return self._id_compra
    @property
    def data(self) -> datetime: 
        return self._data
 
    @property
    def insumo_id(self) -> int | None:
        """
        Valor da FK do insumo (None se o insumo ainda não foi gravado)
        """
        return self._insumo.id
 
    @property
    def variacao(self) -> Decimal:
        """
        Quanto o saldo mudou por causa desta movimentação (positivo soma, negativo subtrai)
        """
        return self._tipo.variacao(self._quantidade)
 
    def __repr__(self) -> str:
        """
        Texto exibido ao imprimir o objeto
        `{x:+}` mostra o sinal explícito (+5 ou -2)
        """
        return f"<MovimentacaoEstoque id={self.id} {self._tipo.value} {self.variacao:+} de {self._insumo.nome!r}>"