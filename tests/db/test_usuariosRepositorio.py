import pytest

from app.models import Administrador
from app.repositories.usuarios_rep import RepositorioUsuarios


@pytest.fixture
def repo_usuarios(conexao, seed):
    """Repositório de usuários usando a conexão de teste (já com o seed carregado)"""
    # O repositório espera uma FUNÇÃO que devolve a conexão: o lambda é essa função
    return RepositorioUsuarios(lambda: conexao)


def test_buscar_por_email_da_administradora_devolve_administrador(repo_usuarios):
    usuario = repo_usuarios.buscarPorEmail("rosangela@confeitaria.local")

    assert isinstance(usuario, Administrador)
    assert usuario.id == 1


def test_buscar_por_email_inexistente_devolve_none(repo_usuarios):
    usuario = repo_usuarios.buscarPorEmail("ninguem@exemplo.com")

    assert usuario is None
