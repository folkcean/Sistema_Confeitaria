"""
app / models / contratos.py

Contratos(Protocol) das classes que ainda não existem ou que ficam em outro módulo

'Protocol' representa uma lista de métodos que o objeto precisa ter, sem dizer qual é a classe

Pra que serve aqui:
    1. Funcionário e Administrador precisam chamar Pedido e Estoque, que ainda não foram escritos
       O contrato descreve o que é esperado deles

"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from .cobranca import Cobranca
from .enums import StatusPedido
from .estoque import Estoque


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


class Recomendador(Protocol):
    """
    Módulo que sugere compras de reposição
    A implementação real é a RecomendadorIA (app / services / recomendador_ia.py)
    """

    def recomendar(self, contexto: dict) -> dict:
        """
        Recebe o retrato do banco (RepositorioContextoIA.montar) e devolve resumo, recomendações e avisos
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


class GatewayPagamento(Protocol):
    """
    Gateway de pagamento que cria e consulta cobranças Pix
    A implementação real é a GatewayAbacatePay (app / services / gateway_abacatepay.py);
    nos testes entra a GatewayFalso (tests / falsos.py), que não usa internet
    """

    def criarPix(self, valor: Decimal, referencia: str, descricao: str) -> Cobranca:
        """
        Cria um Pix de 'valor' reais. 'referencia' identifica a cobrança no nosso sistema (ex.: 'pedido-6-sinal')
        """
        ...

    def consultar(self, id_cobranca: str) -> Cobranca:
        """
        Busca a cobrança inteira (status e QR Code) pelo id do gateway
        """
        ...

    def simularPagamento(self, id_cobranca: str) -> Cobranca:
        """
        Só no modo de teste: simula que o cliente pagou o Pix
        """
        ...

class EnviadorEmail(Protocol):
    """
    Serviço que envia emails de texto
    A implementação real é a EnviadorEmailSMTP (app / services / envio_email.py)
    em desenvolvimento entra a EnviadorEmailNoTerminal, e nos testes a EnviadorFalso (tests / falsos.py
    """
    def enviar(self, destinatario: str, assunto: str, texto: str) -> None:
        """
        Envia um e-mail de texto simples. Levanta EnvioEmailError se não conseguir
        """
        ...

class ModeloLinguagem(Protocol):
    """
    API de IA que responde a uma mensagem seguindo as instruções
    A implementação real é a GatewayIA (app / services / gateway_ia.py); nos testes, ModeloFalso
    """

    def responder(self, instrucoes: str, mensagem: str, esquema: dict | None = None) -> str:
        """
        Texto da resposta. Com 'esquema' (JSON Schema), a resposta é um JSON nesse formato
        """
        ...
