"""
tests / falsos.py

Dublês ("falsos") usados nos testes no lugar de serviços de fora
"""
from dataclasses import replace
from decimal import Decimal

from app.exceptions import GatewayPagamentoError
from app.models.cobranca import Cobranca
from app.validators.campos import garantir


class GatewayFalso:
    def __init__(self):
        self.cobrancas: dict[str, Cobranca] = {}
        self.chamadas = 0
        self.ultimo_valor: Decimal | None = None
        self._id_por_referencia: dict[str, str] = {}

    # Contrato GatewayPagamento
    def criarPix(self, valor: Decimal, referencia: str, descricao: str) -> Cobranca:
        self.chamadas += 1
        self.ultimo_valor = valor
        existente = self.cobrancas.get(self._id_por_referencia.get(referencia, ""))
        pendente = bool(existente) and existente.status == "PENDING"
        escolhas = {True: lambda: existente, False: lambda: self._novoPix(referencia)}
        return escolhas[pendente]()

    def consultar(self, id_cobranca: str) -> Cobranca:
        """Devolve a cobrança guardada"""
        self.chamadas += 1
        garantir(id_cobranca in self.cobrancas, GatewayPagamentoError("Pix QR Code not found"))
        return self.cobrancas[id_cobranca]

    def simularPagamento(self, id_cobranca: str) -> Cobranca:
        cobranca = self.consultar(id_cobranca)
        garantir(cobranca.status == "PENDING", GatewayPagamentoError("Só dá para simular Pix pendente"))
        return self._trocarStatus(id_cobranca, "PAID")

    # Ajudas para os testes
    def vencer(self, id_cobranca: str) -> Cobranca:
        return self._trocarStatus(id_cobranca, "EXPIRED")

    def _novoPix(self, referencia: str) -> Cobranca:
        id_novo = f"pix_char_falso_{len(self.cobrancas) + 1}"
        cobranca = Cobranca(
            id=id_novo, status="PENDING", br_code="00020101021126580014BR.GOV.BCB.PIX-falso",
            br_code_base64="data:image/png;base64,iVBORw0KGgo=", dev_mode=True,
        )
        self.cobrancas[id_novo] = cobranca
        self._id_por_referencia[referencia] = id_novo
        return cobranca

    def _trocarStatus(self, id_cobranca: str, status: str) -> Cobranca:
        self.cobrancas[id_cobranca] = replace(self.cobrancas[id_cobranca], status=status)
        return self.cobrancas[id_cobranca]
