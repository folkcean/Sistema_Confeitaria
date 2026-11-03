import pytest

from app.repositories.produtos_rep import RepositorioProdutos


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
