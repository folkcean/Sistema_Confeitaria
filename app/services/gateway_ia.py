"""
app / services / gateway_ia.py

"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.exceptions import GatewayIAError
from app.validators.campos import garantir

TEMPO_LIMITE_EM_SEGUNDOS = 60
# Teto da resposta (o raciocínio dos modelos que "pensam" também conta aqui)
MAXIMO_TOKENS_RESPOSTA = 3000
# Quanto o modelo "pensa" antes de responder. O padrão do gpt-oss é "medium", que gasta o teto acima
# antes de fechar o JSON. Num modelo que não pensa (ex.: Llama), apague o reasoning_effort do corpo
ESFORCO_RACIOCINIO = "low"


class GatewayIA:
    """
    Manda as instruções e a mensagem para a API de IA e devolve o texto da resposta
    """

    def __init__(self, url_base: str, chave_api: str, modelo: str):
        self._url_base = url_base.rstrip("/")
        self._chave_api = chave_api
        self._modelo = modelo

    # Operação do contrato ModeloLinguagem
    def responder(self, instrucoes: str, mensagem: str, esquema: dict | None = None) -> str:
        garantir(self._chave_api, GatewayIAError("Falta a IA_CHAVE no .env."))
        corpo = {
            "model": self._modelo,
            "messages": [
                {"role": "system", "content": instrucoes},
                {"role": "user", "content": mensagem},
            ],
            "temperature": 0.2,
            "max_completion_tokens": MAXIMO_TOKENS_RESPOSTA,
            "reasoning_effort": ESFORCO_RACIOCINIO,
        }
        # `and`: sem esquema não manda response_format (resposta em texto livre)
        esquema and corpo.update(response_format={
            "type": "json_schema",
            "json_schema": {"name": "resposta", "strict": True, "schema": esquema},
        })
        escolha = self._enviar(corpo)["choices"][0]
        # "length": o teto de tokens acabou no meio da resposta
        garantir(
            escolha.get("finish_reason") != "length",
            GatewayIAError("A resposta da IA veio cortada. Aumente o MAXIMO_TOKENS_RESPOSTA."),
        )
        return escolha["message"]["content"] or ""

    # Parte interna: HTTP e tradução dos erros
    def _enviar(self, corpo: dict) -> dict:
        """
        Faz o POST em /chat/completions e devolve o JSON da resposta
        """
        requisicao = urllib.request.Request(
            self._url_base + "/chat/completions",
            data=json.dumps(corpo).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._chave_api}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "SistemaConfeitaria/1.0",
            },
        )
        try:
            with urllib.request.urlopen(requisicao, timeout=TEMPO_LIMITE_EM_SEGUNDOS) as resposta:
                return json.load(resposta)
        except urllib.error.HTTPError as erro:
            raise GatewayIAError(self._mensagemDoErro(erro)) from erro
        except (urllib.error.URLError, TimeoutError) as erro:
            raise GatewayIAError(f"Não foi possível falar com a API de IA: {erro}") from erro

    @staticmethod
    def _mensagemDoErro(erro: urllib.error.HTTPError) -> str:
        """{"error": {"message": ...}} da API; corpo que não é JSON (ex.: página HTML) vira só o código"""
        try:
            detalhe = json.load(erro)
        except ValueError:
            return f"A API de IA respondeu {erro.code}"
        detalhe = (isinstance(detalhe, list) and detalhe[0]) or detalhe
        erro_api = detalhe.get("error") or {}
        mensagem = erro_api.get("message") or "erro sem mensagem"
        gerado = (erro_api.get("failed_generation") or "")[:150]
        return f"A API de IA respondeu {erro.code}: {mensagem}" + (gerado and f" (a IA gerou: {gerado})")
