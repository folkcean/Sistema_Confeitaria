from decimal import Decimal

import pytest

from app.exceptions import ValidacaoError
from app.models.opcao_personalizacao import OpcaoPersonalizacao
from app.models.produto import Produto


def novo_produto(**kwargs):
    """Produto mínimo (Bolo, R$ 98); cada teste troca só o que precisa"""
    kwargs.setdefault("nome", "Bolo")
    kwargs.setdefault("preco_base", "98")
    return Produto(**kwargs)


def nova_opcao(nome, custo, **kwargs):
    """Opção de personalização de exemplo"""
    return OpcaoPersonalizacao(nome, custo, **kwargs)


def produto_do_seed():
    """Produto 1 do DB_fill.sql: bolo de chocolate com brigadeiro"""
    return novo_produto(
        custo_mao_de_obra=25,
        margem_lucro="2.50",
        custo_embalagem="3.10",
        percentual_perda=3,
    )


def test_preco_base_vira_decimal_com_duas_casas():
    produto = novo_produto()

    assert produto.preco_base == Decimal("98.00")
    assert str(produto.preco_base) == "98.00"


def test_produto_tem_padroes_de_antecedencia_ativo_descricao_e_tamanho():
    produto = novo_produto()

    assert produto.antecedencia_horas == 48
    assert produto.ativo is True
    assert produto.descricao == ""
    assert produto.tamanho is None


@pytest.mark.parametrize(
    "campo_invalido",
    [
        {"nome": ""},
        {"preco_base": -1},
        {"percentual_perda": 101},
        {"antecedencia_horas": 2.5},
    ],
    ids=["nome_vazio", "preco_negativo", "perda_101", "antecedencia_decimal"],
)
def test_produto_com_dado_invalido_levanta_erro(campo_invalido):
    with pytest.raises(ValidacaoError):
        novo_produto(**campo_invalido)


def test_alterar_preco_invalido_levanta_erro_e_mantem_o_preco():
    produto = novo_produto()

    with pytest.raises(ValidacaoError, match="negativo"):
        produto.alterarPreco(-5)

    assert produto.preco_base == Decimal("98.00")


def test_alterar_descricao_vazia_vira_texto_vazio():
    produto = novo_produto(descricao="Chocolate")

    produto.alterarDescricao(" ")

    assert produto.descricao == ""


def test_alternar_ativo_duas_vezes_muda_o_repr():
    produto = novo_produto()

    produto.alternarAtivo()
    assert produto.ativo is False
    assert "Inativo" in repr(produto)

    produto.alternarAtivo()
    assert produto.ativo is True
    assert "Inativo" not in repr(produto)


# Preço e custo
def test_calcular_preco_sem_opcoes_devolve_o_preco_base():
    assert novo_produto().calcularPreco() == Decimal("98.00")


def test_calcular_preco_soma_o_custo_das_opcoes_escolhidas():
    produto = novo_produto()
    nozes = nova_opcao("Nozes", "8.5")
    morango = nova_opcao("Morango extra", "6")
    produto.adicionarOpcao(nozes)
    produto.adicionarOpcao(morango)

    assert produto.calcularPreco([nozes]) == Decimal("106.50")
    assert produto.calcularPreco([nozes, morango]) == Decimal("112.50")


def test_calcular_preco_com_opcao_inativa_levanta_erro_de_indisponivel():
    produto = novo_produto()
    nozes = nova_opcao("Nozes", "8.5", ativo=False)
    produto.adicionarOpcao(nozes)

    with pytest.raises(ValidacaoError, match="indisponível"):
        produto.calcularPreco([nozes])


def test_calcular_preco_com_opcao_de_outro_produto_levanta_erro():
    produto = novo_produto()
    outro_produto = novo_produto(nome="Torta")
    nozes = nova_opcao("Nozes", "8.5")
    outro_produto.adicionarOpcao(nozes)

    with pytest.raises(ValidacaoError, match="não pertence a este produto"):
        produto.calcularPreco([nozes])


def test_custo_total_com_os_numeros_do_seed():
    # 42,48 x 1,03 + 25 + 3,10 + 0 = 71,85
    assert produto_do_seed().custoTotal("42.48") == Decimal("71.85")  # type: ignore


def test_preco_sugerido_soma_a_margem_ao_custo_total():
    # 71,85 + 2,50 = 74,35
    assert produto_do_seed().precoSugerido("42.48") == Decimal("74.35")  # type: ignore


def test_custo_total_sem_ingredientes_so_soma_os_custos_fixos():
    # 25 + 3,10 = 28,10
    assert produto_do_seed().custoTotal() == Decimal("28.10")


def test_custo_total_com_ingredientes_negativos_levanta_erro():
    with pytest.raises(ValidacaoError, match="negativo"):
        produto_do_seed().custoTotal(-1)


# Descobertas
@pytest.mark.xfail(
    reason="custoTotal usa quantize sem rounding=: 1,265 vira 1,26 (HALF_EVEN) em vez de 1,27",
    strict=True,
)
def test_custo_total_arredonda_meio_para_cima():
    produto = novo_produto(percentual_perda=15)

    assert produto.custoTotal("1.10") == Decimal("1.27")  # type: ignore


@pytest.mark.xfail(
    reason="disponibilidade é texto livre ('Sob encomenda'); o CHECK do banco só aceita 'pronta_entrega' ou 'encomenda'",
    strict=True,
)
def test_disponibilidade_padrao_e_aceita_pelo_banco():
    assert novo_produto().disponibilidade in {"pronta_entrega", "encomenda"}
