import pytest

from app.exceptions import ValidacaoError
from app.models import Fornecedor
from app.repositories.fornecedores_rep import RepositorioFornecedores


@pytest.fixture
def repo_fornecedores(conexao, seed):
    # O repositório espera uma FUNÇÃO que devolve a conexão: o lambda é essa função
    return RepositorioFornecedores(lambda: conexao)


def test_buscar_por_id_traz_fornecedor_do_seed(repo_fornecedores):
    fornecedor = repo_fornecedores.buscarPorId(2)

    assert fornecedor.nome == "Casa do Confeiteiro"
    assert fornecedor.cnpj == "23456789000101"
    assert fornecedor.contato_principal == "Ana"
    assert fornecedor.ativo


def test_salvar_novo_e_recarregar(repo_fornecedores):
    novo = Fornecedor(
        "Laticínios Norte",
        "(22) 2733-4444",
        "Rua do Gás, 120, Centro",
        email="vendas@laticiniosnorte.local",
        cnpj="45.678.901/0001-23",
    )

    repo_fornecedores.salvar(novo)
    assert novo.id is not None

    recarregado = repo_fornecedores.buscarPorId(novo.id)
    assert recarregado is not novo
    assert recarregado.nome == "Laticínios Norte"
    assert recarregado.telefone == "2227334444"
    assert recarregado.cnpj == "45678901000123"
    assert recarregado.contato_principal is None
    assert recarregado.ativo


def test_cnpj_repetido_levanta_validacao_error(repo_fornecedores):
    # Mesmo CNPJ do Atacadao Campos (id 1 no seed)
    repetido = Fornecedor(
        "Outro Atacado",
        "2227335555",
        "Rua Qualquer, 1",
        cnpj="12345678000190",
    )

    with pytest.raises(ValidacaoError, match="Já existe um fornecedor com esse CNPJ."):
        repo_fornecedores.salvar(repetido)
