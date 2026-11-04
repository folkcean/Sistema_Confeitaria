"""
tests/models/test_receita.py

Como rodar só esse arquivo:   pytest tests/models/test_receita.py -v
"""
from decimal import Decimal

import pytest

from app.exceptions import ValidacaoError
from app.models.receita import ItemReceita, Receita


@pytest.fixture
def massa(farinha, leite_condensado):
    """
    Receita que rende 1 un e usa 300 g de farinha e 395 g (1 lata) de leite condensado
    """
    receita = Receita(1, "un", tempo_preparo=60)
    receita.adicionarItem(ItemReceita(farinha, 300))
    receita.adicionarItem(ItemReceita(leite_condensado, 395))
    return receita


# Criação
def test_valores_padrao():
    r = Receita(1, "un")
    assert r.rendimento_qtd == Decimal("1.000")
    assert r.rendimento_un == "un"
    assert r.tempo_preparo == 0
    assert r.modo_preparo is None        # coluna nula
    assert r.complexidade is None        # coluna nula
    assert r.ativa is True               # padrão do DER
    assert r.itens == ()


@pytest.mark.parametrize("rendimento", [0, -1, "abc", None])
def test_rendimento_invalido(rendimento):
    """
    O rendimento precisa ser maior que zero (senão a regra de três divide por zero)
    """
    with pytest.raises(ValidacaoError):
        Receita(rendimento, "un")


@pytest.mark.parametrize("unidade", ["", "   ", None])
def test_unidade_do_rendimento_obrigatoria(unidade):
    with pytest.raises(ValidacaoError):
        Receita(1, unidade)


@pytest.mark.parametrize("tempo", [-1, 1.5, "60", True])
def test_tempo_de_preparo_inteiro_nao_negativo(tempo):
    with pytest.raises(ValidacaoError):
        Receita(1, "un", tempo_preparo=tempo)


# ALTERAÇÕES
def test_alternar_ativa():
    r = Receita(1, "un")
    r.alternarAtiva()
    assert r.ativa is False


def test_alterar_rendimento():
    r = Receita(1, "un")
    r.alterarRendimento(50, "brigadeiros")
    assert r.rendimento_qtd == Decimal("50.000")
    assert r.rendimento_un == "brigadeiros"


def test_alterar_rendimento_invalido_mantem_antigo():
    r = Receita(1, "un")
    with pytest.raises(ValidacaoError):
        r.alterarRendimento(0, "un")
    assert r.rendimento_qtd == Decimal("1.000")


def test_alterar_modo_de_preparo():
    r = Receita(1, "un")
    r.alterarModoPreparo("Misture tudo.")
    assert r.modo_preparo == "Misture tudo."
    r.alterarModoPreparo("")
    assert r.modo_preparo is None


# Itens
@pytest.mark.parametrize("quantidade", [0, -5, "abc", None])
def test_quantidade_do_item_invalida(farinha, quantidade):
    with pytest.raises(ValidacaoError):
        ItemReceita(farinha, quantidade)


def test_adicionar_item_cria_vinculo(farinha):
    r = Receita(1, "un")
    r.atribuirID(3)
    item = ItemReceita(farinha, 300)
    r.adicionarItem(item)
    assert r.itens == (item,)
    assert item.receita is r
    assert item.receita_id == 3
    assert item.insumo is farinha


def test_mesmo_insumo_nao_entra_duas_vezes(farinha):
    r = Receita(1, "un")
    r.adicionarItem(ItemReceita(farinha, 300))
    with pytest.raises(ValidacaoError):
        r.adicionarItem(ItemReceita(farinha, 100))


def test_item_nao_pode_ter_duas_receitas(farinha):
    item = ItemReceita(farinha, 300)
    Receita(1, "un").adicionarItem(item)
    with pytest.raises(ValidacaoError):
        Receita(1, "un").adicionarItem(item)


def test_remover_item_desfaz_vinculo(farinha):
    r = Receita(1, "un")
    item = ItemReceita(farinha, 300)
    r.adicionarItem(item)
    r.removerItem(item)
    assert r.itens == ()
    assert item.receita is None


def test_remover_item_de_outra_receita_falha(farinha):
    with pytest.raises(ValidacaoError):
        Receita(1, "un").removerItem(ItemReceita(farinha, 300))


def test_alterar_quantidade_do_item(farinha):
    item = ItemReceita(farinha, 300)
    item.alterarQuantidade(450)
    assert item.quantidade_necessaria == Decimal("450.000")
    with pytest.raises(ValidacaoError):
        item.alterarQuantidade(0)


def test_itens_devolve_copia_protegida(farinha):
    """
    `itens` é uma tupla: não dá para alterar a lista interna por fora
    """
    r = Receita(1, "un")
    r.adicionarItem(ItemReceita(farinha, 300))
    with pytest.raises(AttributeError):
        r.itens.append(None)


# Escala
def test_necessidades_base_sao_as_quantidades_da_receita(massa, farinha, leite_condensado):
    assert massa.necessidadesBase() == [(farinha, Decimal("300.000")), (leite_condensado, Decimal("395.000"))]


def test_escalar_multiplica_pela_proporcao(massa, farinha, leite_condensado):
    """
    Rende 1 e quero 3: tudo x3
    """
    assert massa.escalar(3) == [(farinha, Decimal("900.000")), (leite_condensado, Decimal("1185.000"))]


def test_escalar_regra_de_tres_com_rendimento_maior(leite_condensado):
    """
    Rende 50 un e usa 400 g; para 12 un: 400 x 12 / 50 = 96 g
    """
    r = Receita(50, "un")
    r.adicionarItem(ItemReceita(leite_condensado, 400))
    assert r.escalar(12) == [(leite_condensado, Decimal("96.000"))]


def test_escalar_arredonda_para_cima(farinha):
    """
    1 g para rendimento 3, produzindo 1: 1/3 = 0,3333... -> 0,334 (nunca subestima o consumo)
    """
    r = Receita(3, "un")
    r.adicionarItem(ItemReceita(farinha, 1))
    assert r.escalar(1) == [(farinha, Decimal("0.334"))]


@pytest.mark.parametrize("quantidade", [0, -1, "abc", None])
def test_escalar_quantidade_invalida(massa, quantidade):
    with pytest.raises(ValidacaoError):
        massa.escalar(quantidade)


def test_escalar_receita_sem_itens_devolve_lista_vazia():
    assert Receita(1, "un").escalar(5) == []


def test_escalar_no_formato_que_o_estoque_consome(massa, estoque, farinha, leite_condensado):
    """
    Integração: o resultado de escalar() entra direto em Estoque.consumir()
    """
    estoque.consumir(massa.escalar(2))
    assert farinha.quantidade_atual == Decimal("9.400")        # 10 kg - 600 g
    assert leite_condensado.quantidade_atual == Decimal("38.000")   # 40 - 2 latas