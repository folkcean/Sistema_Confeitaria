import pytest

from app.exceptions import ValidacaoError
from app.models.base import Entidade


def test_entidade_sem_id_tem_id_none():
    assert Entidade().id is None


def test_entidade_criada_com_id_guarda_o_id():
    assert Entidade(7).id == 7


def test_atribuir_id_define_o_id_da_entidade_sem_id():
    entidade = Entidade()

    entidade.atribuirID(5)

    assert entidade.id == 5


def test_atribuir_id_duas_vezes_levanta_erro():
    entidade = Entidade()
    entidade.atribuirID(5)

    with pytest.raises(ValidacaoError, match="não alterável"):
        entidade.atribuirID(6)

    assert entidade.id == 5


def test_atribuir_id_em_entidade_criada_com_id_levanta_erro():
    entidade = Entidade(7)

    with pytest.raises(ValidacaoError, match="não alterável"):
        entidade.atribuirID(9)

    assert entidade.id == 7


def test_id_nao_pode_ser_atribuido_diretamente():
    entidade = Entidade()

    with pytest.raises(AttributeError):
        entidade.id = 9  # type: ignore
