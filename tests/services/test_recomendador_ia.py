"""
tests / services / test_recomendador_ia.py

services/recomendador_ia.py: o que vai para a IA (instruções, dados e esquema) e o que
acontece quando a resposta vem fora do combinado. Usa o ModeloFalso: nada vai para a internet
"""
import json
from datetime import date
from decimal import Decimal

import pytest

from app.exceptions import GatewayIAError, ValidacaoError
from app.services.recomendador_ia import ESQUEMA_RECOMENDACOES, RecomendadorIA
from tests.falsos import ModeloFalso

# Um retrato mínimo do banco, com Decimal e date como o psycopg devolve
CONTEXTO = {
    "hoje": date(2026, 11, 17),
    "insumos": [{"insumo": "Acucar refinado", "saldo": Decimal("8.73"), "minimo": Decimal("10.00")}],
}


def test_recomendar_manda_instrucoes_dados_e_esquema():
    modelo = ModeloFalso()

    resultado = RecomendadorIA(modelo, "REGRAS").recomendar(CONTEXTO)

    chamada = modelo.chamadas[0]
    assert chamada["instrucoes"] == "REGRAS"
    assert chamada["esquema"] == ESQUEMA_RECOMENDACOES
    # Decimal e date viram texto no JSON (default=str), sem perder casas decimais
    assert '"saldo":"8.73"' in chamada["mensagem"]
    assert '"hoje":"2026-11-17"' in chamada["mensagem"]
    assert resultado["recomendacoes"][0]["insumo"] == "Acucar refinado"


def test_resposta_que_nao_e_json_vira_erro_da_ia():
    modelo = ModeloFalso(resposta="Claro! Aqui está:")

    with pytest.raises(GatewayIAError, match="fora do formato"):
        RecomendadorIA(modelo, "REGRAS").recomendar(CONTEXTO)


def test_json_sem_a_lista_vira_erro_da_ia():
    modelo = ModeloFalso(resposta=json.dumps({"resumo": "ok"}))

    with pytest.raises(GatewayIAError, match="sem a lista"):
        RecomendadorIA(modelo, "REGRAS").recomendar(CONTEXTO)


def test_pergunta_vai_sem_esquema_e_volta_em_texto():
    modelo = ModeloFalso(resposta="Vai faltar leite condensado.")

    resposta = RecomendadorIA(modelo, "REGRAS").perguntar(CONTEXTO, "  O que vai faltar?  ")

    assert resposta == "Vai faltar leite condensado."
    assert modelo.chamadas[0]["esquema"] is None
    # A pergunta vai no fim da mensagem, sem os espaços das pontas
    assert modelo.chamadas[0]["mensagem"].endswith("O que vai faltar?")


def test_pergunta_vazia_nem_chama_a_ia():
    modelo = ModeloFalso()

    with pytest.raises(ValidacaoError, match="Escreva a pergunta"):
        RecomendadorIA(modelo, "REGRAS").perguntar(CONTEXTO, "   ")

    assert modelo.chamadas == []


def test_pergunta_longa_demais_nem_chama_a_ia():
    modelo = ModeloFalso()

    with pytest.raises(ValidacaoError, match="500 caracteres"):
        RecomendadorIA(modelo, "REGRAS").perguntar(CONTEXTO, "a" * 501)

    assert modelo.chamadas == []