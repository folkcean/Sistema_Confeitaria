from decimal import Decimal

import pytest

from app.models import Estoque
from app.repositories.insumos_rep import RepositorioInsumos
from app.repositories.produtos_rep import RepositorioProdutos
from app.repositories.receitas_rep import RepositorioReceita


@pytest.fixture
def repo_produtos(conexao, seed):
    """Repositório de produtos usando a conexão de teste (já com o seed carregado)"""
    # O repositório espera uma FUNÇÃO que devolve a conexão: o lambda é essa função
    return RepositorioProdutos(lambda: conexao)


def test_buscar_produto_por_id_traz_nome_e_opcoes(repo_produtos):
    produto = repo_produtos.buscarPorId(1)

    assert produto.nome == "Bolo de chocolate com brigadeiro"
    assert len(produto.opcoes) > 0


def test_listar_com_busca_so_traz_produtos_com_o_texto_no_nome(repo_produtos):
    produtos = repo_produtos.listar(busca="chocolate")

    # Não pode vir vazio: senão o for de baixo não roda e o teste passaria sem conferir nada
    assert len(produtos) > 0
    for produto in produtos:
        assert "chocolate" in produto.nome.lower()


@pytest.fixture
def estoque(conexao, seed):
    """Estoque com todos os insumos do seed (ativos e inativos)"""
    return Estoque(RepositorioInsumos(lambda: conexao).listar())


@pytest.fixture
def repo_receitas(conexao, seed):
    """Repositório de receitas usando a conexão de teste"""
    return RepositorioReceita(lambda: conexao)


def test_carregar_receitas_liga_as_receitas_do_produto(repo_produtos, repo_receitas, estoque):
    produto = repo_produtos.buscarPorId(1)
    repo_produtos.carregarReceitas([produto], repo_receitas, estoque)

    assert len(produto.receitas) == 2
    assert {ligacao.receita.id for ligacao in produto.receitas} == {2, 8}
    assert {ligacao.quantidade for ligacao in produto.receitas} == {Decimal("1"), Decimal("1.5")}


def test_insumos_das_receitas_carregadas_sao_os_do_estoque(repo_produtos, repo_receitas, estoque):
    produto = repo_produtos.buscarPorId(1)
    repo_produtos.carregarReceitas([produto], repo_receitas, estoque)

    # Levantaria ValidacaoError se algum insumo não fosse o mesmo objeto do estoque
    estoque.verificarDisponibilidade(produto.necessidades(1))


def test_remover_ligacao_inexistente_devolve_false(repo_produtos):
    assert repo_produtos.removerLigacaoReceita(1, 999) is False
