from decimal import Decimal

import pytest

from app.exceptions import ValidacaoError
from app.models.opcao_personalizacao import OpcaoPersonalizacao
from app.models.produto import Produto


def novo_produto(**kwargs):
    """Produto mínimo (Bolo, R$ 98); cada teste troca só o que precisa"""
    return Produto("Bolo", "98", **kwargs)


def test_opcao_sem_produto_tem_custo_decimal_com_duas_casas():
    opcao = OpcaoPersonalizacao("Nozes", "8.5")  # type: ignore

    assert opcao.custo_adicional == Decimal("8.50")
    assert str(opcao.custo_adicional) == "8.50"
    assert opcao.produto is None


@pytest.mark.parametrize(
    "id_produto, produto_id_esperado",
    [(None, None), (1, 1)],
    ids=["produto_sem_id", "produto_com_id"],
)
def test_adicionar_opcao_liga_os_dois_lados_e_produto_id_depende_do_id_do_produto(
    id_produto, produto_id_esperado
):
    produto = novo_produto(id_produto=id_produto)
    opcao = OpcaoPersonalizacao("Nozes", "8.5")  # type: ignore

    produto.adicionarOpcao(opcao)

    assert opcao.produto is produto
    assert opcao in produto.opcoes
    assert opcao.produto_id == produto_id_esperado


def test_opcao_que_ja_tem_produto_nao_vai_para_outro_produto():
    produto = novo_produto()
    outro_produto = Produto("Torta", "60")
    opcao = OpcaoPersonalizacao("Nozes", "8.5")  # type: ignore
    produto.adicionarOpcao(opcao)

    with pytest.raises(ValidacaoError, match="já pertence a um produto"):
        outro_produto.adicionarOpcao(opcao)

    assert opcao.produto is produto
    assert outro_produto.opcoes == ()


def test_remover_opcao_desfaz_o_vinculo():
    produto = novo_produto()
    opcao = OpcaoPersonalizacao("Nozes", "8.5")  # type: ignore
    produto.adicionarOpcao(opcao)

    produto.removerOpcao(opcao)

    assert opcao.produto is None
    assert produto.opcoes == ()


def test_remover_opcao_de_fora_levanta_erro():
    produto = novo_produto()
    opcao = OpcaoPersonalizacao("Nozes", "8.5")  # type: ignore

    with pytest.raises(ValidacaoError, match="não pertence a este produto"):
        produto.removerOpcao(opcao)


def test_alterar_custo_negativo_levanta_erro():
    opcao = OpcaoPersonalizacao("Nozes", "8.5")  # type: ignore

    with pytest.raises(ValidacaoError, match="negativo"):
        opcao.alterarCusto(-1)

    assert opcao.custo_adicional == Decimal("8.50")
