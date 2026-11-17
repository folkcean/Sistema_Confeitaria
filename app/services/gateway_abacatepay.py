"""
app / services / gateway_abacatepay.py

ADAPTADOR DA ABACATEPAY (padrão Adapter)

É o único arquivo do sistema que conhece a API da AbacatePay
O resto do sistema fala em R$ (Decimal), em português e recebe objetos Cobranca

"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from decimal import Decimal

from app.exceptions import GatewayPagamentoError
from app.models.cobranca import Cobranca
from app.validators.campos import garantir

URL_BASE_API_ABACATEPAY = "https://api.abacatepay.com/v2"
# Validade do Pix em segundos (mínimo da API: 300). Vencido, o próximo acesso gera outro
VALIDADE_PIX_EM_SEGUNDOS = 1800
TEMPO_LIMITE_REQUISICAO_EM_SEGUNDOS = 15


def converterReaisParaCentavos(valor_em_reais: Decimal) -> int:
    return int(valor_em_reais * 100)


class GatewayAbacatePay:
    """
    Cria, consulta e (no Modo Teste) simula o pagamento de Pix na AbacatePay
    A chave define o ambiente: 'abc_dev_...' é o Modo Teste
    """

    def __init__(self, chave_api: str):
        self._chave_api = chave_api

    # Operações do contrato GatewayPagamento (nomes e parâmetros fixados pelo contrato)
    def criarPix(self, valor: Decimal, referencia: str, descricao: str) -> Cobranca:
        """
        Cria o Pix. Com um Pix pendente de mesma 'referencia' (externalId), a API devolve o que já existe
        """
        corpo_requisicao = {
            "method": "PIX",
            "data": {
                "amount": converterReaisParaCentavos(valor),
                "externalId": referencia,
                "description": descricao,
                "expiresIn": VALIDADE_PIX_EM_SEGUNDOS,
                "metadata": {"referencia": referencia},
            },
        }
        dados_cobranca = self._enviarRequisicao("POST", "/transparents/create", corpo_requisicao)
        return self._converterDadosEmCobranca(dados_cobranca)

    def consultar(self, id_cobranca: str) -> Cobranca:
        """Busca o Pix inteiro (status e QR Code) pelo id"""
        caminho_endpoint = self._montarCaminhoComIdNaQuery("/transparents/get", id_cobranca)
        return self._converterDadosEmCobranca(self._enviarRequisicao("GET", caminho_endpoint))

    def simularPagamento(self, id_cobranca: str) -> Cobranca:
        """Só no Modo Teste: marca o Pix como pago (com chave de produção, a API recusa)"""
        caminho_endpoint = self._montarCaminhoComIdNaQuery("/transparents/simulate-payment", id_cobranca)
        return self._converterDadosEmCobranca(self._enviarRequisicao("POST", caminho_endpoint))

    # Parte interna: HTTP e tradução do JSON
    @staticmethod
    def _montarCaminhoComIdNaQuery(caminho_endpoint: str, id_cobranca: str) -> str:
        """Põe o id na query string: /transparents/get?id=pix_char_..."""
        return f"{caminho_endpoint}?{urllib.parse.urlencode({'id': id_cobranca})}"

    def _enviarRequisicao(self, metodo_http: str, caminho_endpoint: str,
                          corpo_requisicao: dict | None = None) -> dict:
        """
        Faz a requisição e devolve os dados do JSON

        LÓGICA:
        1) monta a requisição; sem corpo (GET, simulate) o 'data' do urllib vai None;
        2) 4xx/5xx viram HTTPError, mas o envelope com a mensagem da API está no próprio erro;
        3) sem internet ou DNS vira URLError;
        4) envelope com success false vira GatewayPagamentoError com a mensagem da API
        """
        requisicao_http = urllib.request.Request(
            URL_BASE_API_ABACATEPAY + caminho_endpoint,
            # 'corpo and ...' devolve None quando não há corpo; senão, o JSON em bytes
            data=corpo_requisicao and json.dumps(corpo_requisicao).encode(),
            method=metodo_http,
            headers={
                "Authorization": f"Bearer {self._chave_api}",
                "Content-Type": "application/json",
                "Accept": "application/json",

                #Não me pergunte pq, eu so sei que precisa disso se não a API morre.
                "User-Agent": "SistemaConfeitaria/1.0",
            },
        )
        try:
            with urllib.request.urlopen(requisicao_http, timeout=TEMPO_LIMITE_REQUISICAO_EM_SEGUNDOS) as resposta_http:
                envelope_resposta = json.load(resposta_http)
        except urllib.error.HTTPError as erro_http:
            envelope_resposta = self._lerEnvelopeDaRespostaDeErro(erro_http)
        except urllib.error.URLError as erro_conexao:
            raise GatewayPagamentoError(
                f"Não foi possível falar com a AbacatePay: {erro_conexao.reason}"
            ) from erro_conexao

        garantir(
            envelope_resposta.get("success"),
            GatewayPagamentoError(envelope_resposta.get("error") or "Erro na AbacatePay"),
        )
        return envelope_resposta["data"]

    @staticmethod
    def _lerEnvelopeDaRespostaDeErro(erro_http: urllib.error.HTTPError) -> dict:
        """Lê o envelope de um 4xx/5xx; se o corpo não for JSON (ex.: página de erro), monta um com o código"""
        try:
            return json.load(erro_http)
        except ValueError:
            return {"success": False, "error": f"A AbacatePay respondeu {erro_http.code}"}

    @staticmethod
    def _converterDadosEmCobranca(dados_cobranca: dict) -> Cobranca:
        """Traduz os valores da API para um objeto Cobranca"""
        data_expiracao = dados_cobranca.get("expiresAt") and datetime.fromisoformat(dados_cobranca["expiresAt"])
        return Cobranca(
            id=dados_cobranca["id"],
            status=dados_cobranca["status"],
            br_code=dados_cobranca.get("brCode"),
            br_code_base64=dados_cobranca.get("brCodeBase64"),
            expira_em=data_expiracao or None,
            dev_mode=bool(dados_cobranca.get("devMode")),
        )
