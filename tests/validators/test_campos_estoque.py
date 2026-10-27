"""
tests / validators / test_campos_estoque.py

Testes dos validadores novos (quantidades, custos, ids e Enums)
"""
from decimal import Decimal

import pytest

from app.exceptions import ValidacaoError
from app.models import TipoInsumo
from app.validators.campos import Validador


def test_quantidade_arredonda_para_3_casas():
    assert Validador.quantidade("1.2345", "q") == Decimal("1.235")


# @pytest.mark.parametrize repete o MESMO teste para cada valor da lista (aqui: 5 testes em 1)
@pytest.mark.parametrize("invalido", [-1, "abc", None, float("nan"), 10 ** 8])
def test_quantidade_rejeita_invalidos(invalido):
    with pytest.raises(ValidacaoError):
        Validador.quantidade(invalido, "q")


def test_quantidade_positiva_rejeita_zero():
    with pytest.raises(ValidacaoError):
        Validador.quantidadePositiva(0, "q")


def test_quantidade_ajuste_aceita_negativo_e_rejeita_zero():
    assert Validador.quantidadeAjuste(-2, "q") == Decimal("-2")
    with pytest.raises(ValidacaoError):
        Validador.quantidadeAjuste(0, "q")


def test_custo_unitario_tem_4_casas():
    assert Validador.custoUnitario("1.23456", "c") == Decimal("1.2346")


def test_opcional_se_informado_so_trata_none_como_ausente():
    assert Validador.opcionalSeInformado(Validador.custoUnitario, None, "c") is None
    # 0 NÃO é ausente: é um custo válido (diferente do `opcional`, que trataria 0 como vazio)
    assert Validador.opcionalSeInformado(Validador.custoUnitario, 0, "c") == Decimal("0")


def test_inteiro_positivo():
    assert Validador.inteiroPositivo(3, "id") == 3
    for invalido in (0, -1, True, "3"):
        with pytest.raises(ValidacaoError):
            Validador.inteiroPositivo(invalido, "id")


def test_opcao_de_aceita_texto_e_membro_e_rejeita_invalido():
    assert Validador.opcaoDe(TipoInsumo, "embalagem", "tipo") is TipoInsumo.EMBALAGEM
    assert Validador.opcaoDe(TipoInsumo, TipoInsumo.DECORACAO, "tipo") is TipoInsumo.DECORACAO
    with pytest.raises(ValidacaoError):
        Validador.opcaoDe(TipoInsumo, "outro", "tipo")