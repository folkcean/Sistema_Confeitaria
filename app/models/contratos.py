"""
app / models / contratos.py

Contratos(Protocol) das classes que ainda não existem ou que ficam em outro módulo

'Protocol' representa uma lista de métodos que o objeto precisa ter, sem dizer qual é a classe

Pra que serve aqui:
    1. Funcionário e Administrador precisam chamar Pedido e Estoque, que ainda não foram escritos
       O contrato descreve o que é esperado deles

"""

from __future__ import annotations

from typing import Protocol

from .enums import StatusPedido


# '...'
# Em um Protocol o método só descreve a assinatura, sem implementar, então o corpo fica sendo '...'
class PedidoAvancavel(Protocol):
    """
    Pedido que sabe mudar de status seguindo o fluxo
    """

    def avancarStatus(self, novo_status: StatusPedido) -> None:
        """
        Muda o status do pedido, validando a transição
        """
        ...


class Estoque(Protocol):
    """
    Estoque que pode ser consultado e ajustado
    """

    def resumo(self) -> list[dict]:
        """
        Devolve a situação atual de cada ingrediente
        """
        ...

    def ajustarManual(self, ingrediente, nova_quantidade: float, motivo: str) -> None:
        """
        Ajusta a quantidade de um ingrediente (MOVIMENTACAO_ESTOQUE do tipo 'ajuste')
        """
        ...


class Recomendador(Protocol):
    """
    Módulo que sugere compras de reposição
    """

    def recomendar(self, estoque: Estoque, historico) -> list[dict]:
        """
        Devolve a lista de itens a repor
        """
        ...


class ClienteConsultavel(Protocol):
    """
    Cliente que sabe montar os dados que cada perfil pode ver
    """

    def dadosCompletos(self, solicitante) -> dict:
        """
        Todos os dados (inclui CPF, que é conferido novamente pelo próprio cliente)
        """
        ...

    def dadosOperacionais(self) -> dict:
        """
        Só o que a produção/entrega precisa
        """
        ...
