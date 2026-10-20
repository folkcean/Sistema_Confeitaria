"""
app / models / enums.py

Valores fixos do sistema

Lista fechada de opções com nome -> exemplo: troca o uso de vários 'em_producao' espalhados pelo código por 'StatusPedido.EM_PRODUCAO'
"""

from enum import Enum

from app.exceptions import TransicaoStatusError
from app.validators.campos import garantir


class Perfil(Enum):
    """
    Tipo de usuário (subtipos de USUÁRIO no DER)
    """

    CLIENTE = "cliente"
    FUNCIONARIO = "funcionario"
    ADMINISTRADOR = "administrador"


class StatusPedido(Enum):
    """
    PEDIDO.status e as regras de mudança entre status

    Fluxo da entrevista:
    solicitado -> orcamento -> (sinal de 50%) -> confirmado -> em_producao -> pronto -> entregue -> finalizado
    O cancelamento só ocorre depois de confirmado, exige motivo e não tem reembolso.
    """

    SOLICITADO = "solicitado"
    ORCAMENTO = "orcamento"
    CONFIRMADO = "confirmado"
    EM_PRODUCAO = "em_producao"
    PRONTO = "pronto"
    ENTREGUE = "entregue"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"

    def proximos(self) -> frozenset["StatusPedido"]:
        """
        Status para os quais este pode avançar. Consulta a tabela _TRANSICOES
        """
        return _TRANSICOES[self]

    def podeIrPara(self, destino: "StatusPedido") -> bool:
        """
        True se o fluxo permite ir deste status para `destino`
        """
        return destino in self.proximos()

    def validarTransicao(self, destino: "StatusPedido") -> None:
        """
        Levanta TransicaoStatusError se a mudança não for permitida
        """
        garantir(
            self.podeIrPara(destino),
            TransicaoStatusError(
                f"Não é possível mudar o pedido de '{self.value}' para '{destino.value}'"
            ),
        )

    def exigeMotivo(self) -> bool:
        """
        Cancelamento exige motivo (PEDIDO.motivo_cancelamento)
        """
        return self is StatusPedido.CANCELADO


# Tabela do fluxo: status atual -> status permitidos em seguida.
# A regra "sinal de 50% pago antes de confirmar" depende de status_pagamento e deve ser conferida na classe Pedido
_TRANSICOES = {
    StatusPedido.SOLICITADO: frozenset({StatusPedido.ORCAMENTO}),
    StatusPedido.ORCAMENTO: frozenset({StatusPedido.CONFIRMADO}),
    StatusPedido.CONFIRMADO: frozenset(
        {StatusPedido.EM_PRODUCAO, StatusPedido.CANCELADO}
    ),
    StatusPedido.EM_PRODUCAO: frozenset({StatusPedido.PRONTO, StatusPedido.CANCELADO}),
    StatusPedido.PRONTO: frozenset({StatusPedido.ENTREGUE, StatusPedido.CANCELADO}),
    StatusPedido.ENTREGUE: frozenset({StatusPedido.FINALIZADO}),
    StatusPedido.FINALIZADO: frozenset(),
    StatusPedido.CANCELADO: frozenset(),
}


class StatusPagamento(Enum):
    """
    PEDIDO.status_pagamento
    """

    AGUARDANDO_SINAL = "aguardando_sinal"
    SINAL_PAGO = "sinal_pago"
    PAGO = "pago"


class TipoEntrega(Enum):
    """
    PEDIDO.tipo_entrega
    """

    ENTREGA = "entrega"
    RETIRADA = "retirada"


class FormaPagamento(Enum):
    """
    PEDIDO.forma_pagamento_sinal e forma_pagamento_restante
    """

    PIX = "pix"
    DINHEIRO = "dinheiro"
    CARTAO = "cartao"


class TipoMovimentacao(Enum):
    """
    MOVIMENTACAO_ESTOQUE.tipo
    """

    ENTRADA = "entrada"
    CONSUMO = "consumo"
    PERDA = "perda"
    AJUSTE = "ajuste"


class StatusCompra(Enum):
    """
    COMPRA.status
    """

    PENDENTE = "pendente"
    RECEBIDA = "recebida"
    CANCELADA = "cancelada"


class TipoInsumo(Enum):
    """
    INGREDIENTE.tipo
    """

    INGREDIENTE = "ingrediente"
    EMBALAGEM = "embalagem"
    DECORACAO = "decoracao"
