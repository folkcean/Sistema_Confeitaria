"""
tests/services/test_precificacao.py

Cenário usado (números fáceis de conferir à mão):
    ingredientes: 500 g de farinha (R$ 8,00/kg -> R$ 4,00) + 395 g de leite condensado (1 lata, R$ 6,50) = R$ 10,50
    perda de 10% sobre os ingredientes: 10,50 x 1,10 = R$ 11,55
    + mão de obra R$ 20 + embalagem R$ 5 + indireto R$ 5 = custo unitário R$ 41,55
    preço = 41,55 x 2,5 = 103,875 -> arredonda (meio para cima) para R$ 103,88

As faixas de entrega usadas aqui são as estimativas da calculadora


Como rodar só esse arquivo:   pytest tests/services/test_precificacao.py -v
"""
from decimal import Decimal

import pytest

from app.exceptions import ValidacaoError
from app.models.enums import TipoEntrega
from app.models.insumo import Insumo
from app.models.opcao_personalizacao import OpcaoPersonalizacao
from app.models.produto import Produto
from app.models.receita import ItemReceita, Receita
from app.services.precificacao import CalculadoraPreco


@pytest.fixture
def farinha():
    return Insumo("Farinha", "kg", "g", fator_conversao=1000, quantidade_atual=10, custo_por_unidade=Decimal("8"))


@pytest.fixture
def leite():
    return Insumo("Leite condensado", "lata", "g", fator_conversao=395, quantidade_atual=40,
                  custo_por_unidade=Decimal("6.5"))


@pytest.fixture
def bolo(farinha, leite):
    """
    Bolo do cenário descrito no topo do arquivo
    """
    receita = Receita(1, "un")
    receita.adicionarItem(ItemReceita(farinha, 500))
    receita.adicionarItem(ItemReceita(leite, 395))
    produto = Produto("Bolo", 90, custo_mao_de_obra=20, custo_embalagem=5, custo_indireto=5, percentual_perda=10)
    produto.adicionarReceita(receita)
    return produto


@pytest.fixture
def calc():
    return CalculadoraPreco()


# CUSTO E PREÇO
def test_custo_dos_ingredientes(calc, bolo):
    assert calc.custoIngredientes(bolo) == Decimal("10.50")


def test_custo_dos_ingredientes_de_varias_unidades(calc, bolo):
    assert calc.custoIngredientes(bolo, 2) == Decimal("21.00")


def test_custo_unitario_aplica_perda_e_soma_o_resto(calc, bolo):
    assert calc.custoUnitario(bolo) == Decimal("41.55")


def test_preco_unitario_usa_multiplicador_padrao_e_arredonda(calc, bolo):
    """
    103,875 arredonda para 103,88 (meio para cima)
    """
    assert calc.precoUnitario(bolo) == Decimal("103.88")


def test_multiplicador_padrao_e_dois_e_meio(calc):
    assert calc.multiplicador_margem == Decimal("2.500")


def test_multiplicador_personalizado(bolo):
    assert CalculadoraPreco(multiplicador_margem=3).precoUnitario(bolo) == Decimal("124.65")


@pytest.mark.parametrize("multiplicador", [0, -1, "abc", Decimal("0.9")])
def test_multiplicador_invalido(multiplicador):
    """
    Zero, negativo, texto e menor que 1 (venderia abaixo do custo) são recusados
    """
    with pytest.raises(ValidacaoError):
        CalculadoraPreco(multiplicador_margem=multiplicador)


def test_produto_sem_receita_usa_so_os_outros_custos():
    """
    Sem receita, o custo é só mão de obra + embalagem + indireto: (20+5+5) x 2,5 = 75
    """
    produto = Produto("Docinho", 10, custo_mao_de_obra=20, custo_embalagem=5, custo_indireto=5)
    assert CalculadoraPreco().precoUnitario(produto) == Decimal("75.00")


def test_insumo_sem_custo_cadastrado_e_recusado(calc):
    """
    Melhor avisar do que calcular um preço errado com custo zero
    """
    sem_custo = Insumo("Cacau", "kg", "g", fator_conversao=1000)
    receita = Receita(1, "un")
    receita.adicionarItem(ItemReceita(sem_custo, 100))
    produto = Produto("Brownie", 10)
    produto.adicionarReceita(receita)
    with pytest.raises(ValidacaoError):
        calc.custoUnitario(produto)


# Personalização
def test_preco_da_personalizacao(calc):
    """
    Entrevista 5.4: brigadeiro no bolo custa R$ 3,00 cada; 4 brigadeiros = R$ 12,00
    """
    brigadeiro = OpcaoPersonalizacao("Brigadeiro", 3)
    assert calc.precoPersonalizacao([(brigadeiro, 4)]) == Decimal("12.00")


def test_personalizacao_soma_varias_opcoes(calc):
    brigadeiro = OpcaoPersonalizacao("Brigadeiro", 3)
    nozes = OpcaoPersonalizacao("Nozes", "7.50")
    assert calc.precoPersonalizacao([(brigadeiro, 2), (nozes, 1)]) == Decimal("13.50")


def test_sem_personalizacao_custa_zero(calc):
    assert calc.precoPersonalizacao([]) == Decimal("0.00")


# Taxa de entrega
def test_retirada_nao_paga_taxa_mesmo_com_distancia(calc):
    assert calc.taxaEntrega(TipoEntrega.RETIRADA, 30) == Decimal("0.00")


def test_retirada_nao_precisa_de_distancia(calc):
    assert calc.taxaEntrega(TipoEntrega.RETIRADA) == Decimal("0.00")


@pytest.mark.parametrize("distancia, taxa", [
    (0, "5.00"), (1, "5.00"), (2, "5.00"),          # limite da faixa é inclusivo: 2 km ainda é a 1ª faixa
    ("2.1", "8.00"), (5, "8.00"),
    ("5.5", "12.00"), (10, "12.00"),
    (11, "18.00"), (15, "18.00"),
])
def test_taxa_por_faixa_de_distancia(calc, distancia, taxa):
    assert calc.taxaEntrega(TipoEntrega.ENTREGA, distancia) == Decimal(taxa)


def test_acima_da_ultima_faixa_nao_ha_entrega(calc):
    with pytest.raises(ValidacaoError):
        calc.taxaEntrega(TipoEntrega.ENTREGA, "15.1")


def test_entrega_exige_distancia(calc):
    with pytest.raises(ValidacaoError):
        calc.taxaEntrega(TipoEntrega.ENTREGA)


@pytest.mark.parametrize("distancia", [-1, "abc"])
def test_distancia_invalida(calc, distancia):
    with pytest.raises(ValidacaoError):
        calc.taxaEntrega(TipoEntrega.ENTREGA, distancia)


def test_aceita_tipo_de_entrega_como_texto(calc):
    """
    O banco guarda 'entrega'/'retirada' como texto
    """
    assert calc.taxaEntrega("entrega", 3) == Decimal("8.00")


def test_faixas_personalizadas():
    calc = CalculadoraPreco(faixas_entrega=[(3, "4"), (6, "9")])
    assert calc.taxaEntrega(TipoEntrega.ENTREGA, 4) == Decimal("9.00")
    with pytest.raises(ValidacaoError):
        calc.taxaEntrega(TipoEntrega.ENTREGA, 7)


@pytest.mark.parametrize("faixas", [
    [(5, "8"), (2, "5")],            # fora de ordem
    [(2, "5"), (2, "8")],            # distância repetida
    [(0, "5")],                      # limite zero
    [(2, "-5")],                     # taxa negativa
])
def test_faixas_invalidas(faixas):
    with pytest.raises(ValidacaoError):
        CalculadoraPreco(faixas_entrega=faixas)


# Montagem do item
def test_montar_item_fixa_preco_e_custo(calc, bolo):
    item = calc.montarItem(bolo, 2)
    assert item.produto is bolo
    assert item.quantidade == 2
    assert item.preco_unitario == Decimal("103.88")
    assert item.custo_unitario == Decimal("41.55")
    assert item.subtotal == Decimal("207.76")


def test_montar_item_com_personalizacao(calc, bolo):
    brigadeiro = OpcaoPersonalizacao("Brigadeiro", 3)
    bolo.adicionarOpcao(brigadeiro)
    item = calc.montarItem(bolo, 1, escolhas=[(brigadeiro, 4)], personalizacao="Bolo azul")
    assert item.custo_personalizacao == Decimal("12.00")
    assert item.subtotal == Decimal("115.88")
    assert item.personalizacao == "Bolo azul"


def test_montar_item_recusa_opcao_de_outro_produto(calc, bolo):
    estranha = OpcaoPersonalizacao("Estranha", 1)
    with pytest.raises(ValidacaoError):
        calc.montarItem(bolo, 1, escolhas=[(estranha, 1)])


def test_item_montado_nao_muda_se_o_preco_mudar_depois(calc, bolo):
    """
    O preço fica FIXADO no item: mudar o produto depois não altera pedidos antigos
    """
    item = calc.montarItem(bolo, 1)
    bolo.alterarCustoMaoDeObra(100)
    assert item.preco_unitario == Decimal("103.88")