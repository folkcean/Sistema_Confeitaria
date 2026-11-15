import pytest

from app.models import Estoque, ItemReceita, Receita
from app.repositories.insumos_rep import RepositorioInsumos
from app.repositories.receitas_rep import RepositorioReceita


@pytest.fixture
def estoque(conexao, seed):
    """Estoque com todos os insumos do seed (ativos e inativos)"""
    return Estoque(RepositorioInsumos(lambda: conexao).listar())


@pytest.fixture
def repo_receitas(conexao, seed):
    """Repositório de receitas usando a conexão de teste (já com o seed carregado)"""
    # O repositório espera uma FUNÇÃO que devolve a conexão: o lambda é essa função
    return RepositorioReceita(lambda: conexao)


# Leitura

def test_buscar_por_id_traz_nome_e_ingredientes(repo_receitas, estoque):
    receita = repo_receitas.buscarPorId(5, estoque)

    assert receita.nome == "Brigadeiro"
    assert len(receita.itens) == 5


def test_insumos_da_receita_sao_os_mesmos_objetos_do_estoque(repo_receitas, estoque):
    receita = repo_receitas.buscarPorId(5, estoque)

    # O Estoque confere com `is`: se o insumo fosse outro objeto (mesmo com o mesmo id),
    # levantaria ValidacaoError("... não faz parte deste estoque")
    estoque.verificarDisponibilidade(receita.necessidadesBase())


def test_buscar_por_id_inexistente_devolve_none(repo_receitas, estoque):
    assert repo_receitas.buscarPorId(999, estoque) is None


def test_receita_inativa_so_aparece_na_aba_inativas(repo_receitas, estoque):
    # Receita 12 (Brownie) está inativa no seed
    ativas = [receita.id for receita in repo_receitas.listar(estoque)]
    inativas = [receita.id for receita in repo_receitas.listar(estoque, "inativas")]

    assert 12 not in ativas
    assert 12 in inativas


def test_listar_com_busca_so_traz_receitas_com_o_texto_no_nome(repo_receitas, estoque):
    receitas = repo_receitas.listar(estoque, busca="massa")

    # Massa branca, Massa de chocolate e Massa de cenoura
    assert sorted(receita.id for receita in receitas) == [1, 2, 3]
    for receita in receitas:
        assert "massa" in receita.nome.lower()


# Gravação

def test_salvar_receita_nova_grava_nome_e_ingredientes(repo_receitas, estoque):
    receita = Receita(10, "unidades")
    receita.alterarNome("Teste")
    insumos = estoque.insumos
    receita.adicionarItem(ItemReceita(insumos[0], 100))
    receita.adicionarItem(ItemReceita(insumos[1], 50))

    repo_receitas.salvar(receita)
    recarregada = repo_receitas.buscarPorId(receita.id, estoque)

    assert recarregada.nome == "Teste"
    assert len(recarregada.itens) == 2


def test_salvar_receita_existente_substitui_os_ingredientes(repo_receitas, estoque):
    receita = repo_receitas.buscarPorId(1, estoque)
    # receita.itens é uma cópia (tupla): dá para remover da receita enquanto percorre
    for item in receita.itens:
        receita.removerItem(item)
    receita.adicionarItem(ItemReceita(estoque.insumos[0], 100))

    repo_receitas.salvar(receita)
    recarregada = repo_receitas.buscarPorId(1, estoque)

    assert len(recarregada.itens) == 1
