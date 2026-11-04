"""
tests/models/test_produto_receita.py

Como rodar só esse arquivo:   pytest tests/models/test_produto_receita.py -v
"""
from decimal import Decimal

import pytest

from app.exceptions import ValidacaoError
from app.models.produto import Produto
from app.models.receita import ItemReceita, Receita


@pytest.fixture
def massa(farinha):
    """
    Receita que rende 1 un e usa 300 g de farinha
    """
    receita = Receita(1, "un")
    receita.adicionarItem(ItemReceita(farinha, 300))
    return receita


@pytest.fixture
def bolo():
    return Produto("Bolo", 50)


def test_produto_nasce_sem_receitas(bolo):
    assert bolo.receitas == ()


def test_adicionar_receita(bolo, massa):
    ligacao = bolo.adicionarReceita(massa)
    assert bolo.receitas == (ligacao,)
    assert ligacao.receita is massa
    assert ligacao.quantidade == Decimal("1.000")      # padrão do DER


def test_mesma_receita_nao_entra_duas_vezes(bolo, massa):
    bolo.adicionarReceita(massa)
    with pytest.raises(ValidacaoError):
        bolo.adicionarReceita(massa)


@pytest.mark.parametrize("quantidade", [0, -1, "abc", None])
def test_quantidade_da_ligacao_invalida(bolo, massa, quantidade):
    with pytest.raises(ValidacaoError):
        bolo.adicionarReceita(massa, quantidade)


def test_remover_receita(bolo, massa):
    bolo.adicionarReceita(massa)
    bolo.removerReceita(massa)
    assert bolo.receitas == ()


def test_remover_receita_nao_ligada_falha(bolo, massa):
    with pytest.raises(ValidacaoError):
        bolo.removerReceita(massa)


def test_necessidades_de_uma_unidade(bolo, massa, farinha):
    bolo.adicionarReceita(massa)
    assert bolo.necessidades() == [(farinha, Decimal("300.000"))]


def test_necessidades_escalam_com_as_unidades(bolo, massa, farinha):
    bolo.adicionarReceita(massa)
    assert bolo.necessidades(3) == [(farinha, Decimal("900.000"))]


def test_quantidade_da_ligacao_multiplica_a_receita(leite_condensado):
    """
    Caixa com 12 brigadeiros: a receita rende 50 un e usa 400 g; ligação quantidade 12 -> 96 g por caixa
    """
    brigadeiro = Receita(50, "un")
    brigadeiro.adicionarItem(ItemReceita(leite_condensado, 400))
    caixa = Produto("Caixa com 12 brigadeiros", 30)
    caixa.adicionarReceita(brigadeiro, 12)
    assert caixa.necessidades() == [(leite_condensado, Decimal("96.000"))]
    assert caixa.necessidades(2) == [(leite_condensado, Decimal("192.000"))]


def test_varias_receitas_somam_pares_de_todas(bolo, massa, farinha, leite_condensado):
    recheio = Receita(1, "un")
    recheio.adicionarItem(ItemReceita(leite_condensado, 395))
    bolo.adicionarReceita(massa)
    bolo.adicionarReceita(recheio)
    assert bolo.necessidades() == [(farinha, Decimal("300.000")), (leite_condensado, Decimal("395.000"))]


def test_receita_inativa_nao_pode_ser_produzida(bolo, massa):
    bolo.adicionarReceita(massa)
    massa.alternarAtiva()
    with pytest.raises(ValidacaoError):
        bolo.necessidades()


@pytest.mark.parametrize("unidades", [0, -1, 1.5, "2", True])
def test_unidades_invalidas(bolo, massa, unidades):
    bolo.adicionarReceita(massa)
    with pytest.raises(ValidacaoError):
        bolo.necessidades(unidades)


def test_produto_sem_receita_nao_precisa_de_insumos(bolo):
    assert bolo.necessidades(5) == []