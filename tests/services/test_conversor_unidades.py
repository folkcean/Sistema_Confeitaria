"""
tests / services / test_conversor_unidades.py

Para rodar só esse arquivo: pytest tests/services/test_conversor_unidades.py -v
"""
from decimal import Decimal

import pytest

from app.exceptions import ValidacaoError
from app.services.conversor_unidades import ConversorUnidades


@pytest.mark.parametrize("de, para, esperado", [
    ("kg", "g", "1000"),
    ("g", "kg", "0.001"),
    ("l", "ml", "1000"),
    ("ml", "l", "0.001"),
])
def test_fatores_padrao(de, para, esperado):
    """Os pares-padrão da tabela devolvem o fator certo."""
    assert ConversorUnidades.fator(de, para) == Decimal(esperado)


@pytest.mark.parametrize("unidade", ["g", "kg", "ml", "l", "un"])
def test_mesma_unidade_tem_fator_um(unidade):
    """Converter uma unidade nela mesma não muda nada (fator 1)."""
    assert ConversorUnidades.fator(unidade, unidade) == Decimal("1")


def test_ignora_maiusculas_e_espacos():
    """' KG ' e 'kg' são a mesma unidade."""
    assert ConversorUnidades.fator(" KG ", "G") == Decimal("1000")


@pytest.mark.parametrize("de, para", [("kg", "ml"), ("lata", "g"), ("g", "l")])
def test_par_desconhecido_e_recusado(de, para):
    """Par fora da tabela (ou sem sentido, como kg -> ml) levanta ValidacaoError."""
    with pytest.raises(ValidacaoError):
        ConversorUnidades.fator(de, para)


@pytest.mark.parametrize("unidade", ["", "   ", None])
def test_unidade_vazia_e_recusada(unidade):
    with pytest.raises(ValidacaoError):
        ConversorUnidades.fator(unidade, "g")


def test_converter_kg_para_g():
    assert ConversorUnidades.converter("1.5", "kg", "g") == Decimal("1500.000")


def test_converter_g_para_kg():
    assert ConversorUnidades.converter(250, "g", "kg") == Decimal("0.250")


def test_converter_arredonda_em_tres_casas():
    """1 g = 0,001 kg; 1,5 g = 0,0015 kg, que arredonda (meio para cima) para 0,002."""
    assert ConversorUnidades.converter("1.5", "g", "kg") == Decimal("0.002")


@pytest.mark.parametrize("quantidade", [-1, "abc", None])
def test_converter_quantidade_invalida(quantidade):
    """Quantidade negativa, texto ou None é recusada."""
    with pytest.raises(ValidacaoError):
        ConversorUnidades.converter(quantidade, "kg", "g")