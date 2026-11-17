"""
tests / falsos.py

Dublês ("falsos") usados nos testes no lugar de serviços de fora
"""

import json
from dataclasses import replace
from decimal import Decimal

from app.exceptions import GatewayPagamentoError, EnvioEmailError
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



class EnviadorFalso:
    """
    Enviador de e-mail em memória (contrato EnviadorEmail): guarda o que seria enviado, sem rede
    """

    def __init__(self, falhar: bool = False):
        self.enviados: list[dict] = []
        self.falhar = falhar

    def enviar(self, destinatario: str, assunto: str, texto: str) -> None:
        """Anota o e-mail. Com falhar=True, simula servidor de e-mail fora do ar"""
        garantir(not self.falhar, EnvioEmailError("Não foi possível enviar o e-mail agora."))
        self.enviados.append({"para": destinatario, "assunto": assunto, "texto": texto})

class ModeloFalso:
    """
    API de IA em memória (contrato ModeloLinguagem): devolve a resposta combinada e anota as chamadas
    Nenhum teste chama a Groq de verdade: sem internet, sem chave e sem gastar o limite grátis
    """

    # Resposta padrão de um pedido de recomendações (quando a chamada vem com esquema)
    RECOMENDACOES = {
        "resumo": "Açúcar abaixo do mínimo.",
        "recomendacoes": [{
            "insumo": "Acucar refinado", "prioridade": "alta", "comprar": 5, "unidade": "kg",
            "pedir_ate": "2026-11-17", "fornecedor": "", "motivo": "Já está abaixo do mínimo.",
            "fatores": ["saldo 8,73 kg abaixo do mínimo de 10 kg"],
        }],
        "avisos": [],
    }

    def __init__(self, resposta=None, erro=None):
        # resposta: texto fixo que o teste quer receber; erro: exceção que o teste quer ver levantada
        self.resposta = resposta
        self.erro = erro
        self.chamadas = []

    def responder(self, instrucoes, mensagem, esquema=None):
        """Anota a chamada; com erro combinado, levanta; senão devolve a resposta (ou a padrão)"""
        self.chamadas.append({"instrucoes": instrucoes, "mensagem": mensagem, "esquema": esquema})
        # `and`/`or` sem if: só levanta quando o teste combinou um erro
        self.erro and self._levantar()
        # Com esquema é pedido de recomendações (JSON); sem esquema é pergunta livre (texto)
        padrao = (esquema and json.dumps(self.RECOMENDACOES)) or "Resposta de teste."
        return self.resposta or padrao

    def _levantar(self):
        """`raise` é instrução e não cabe numa expressão: por isso fica num método"""
        raise self.erro
