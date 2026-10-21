import pytest

from app.exceptions import SenhaFracaError
from app.models.senha import Senha, SenhaAusente

SENHA_FORTE = "Bolo@2026"


def test_senha_criada_confere_com_a_mesma_senha():
    senha = Senha.criar(SENHA_FORTE)

    assert senha.verificar(SENHA_FORTE) is True


@pytest.mark.parametrize("tentativa", ["errada", None], ids=repr)
def test_verificar_recusa_senha_errada_e_none(tentativa):
    senha = Senha.criar(SENHA_FORTE)

    assert senha.verificar(tentativa) is False


def test_criar_com_senha_fraca_levanta_erro():
    with pytest.raises(SenhaFracaError):
        Senha.criar("fraca")


def test_mesma_senha_gera_hashes_diferentes():
    primeira = Senha.criar(SENHA_FORTE)
    segunda = Senha.criar(SENHA_FORTE)

    assert primeira.hash != segunda.hash


def test_hash_nunca_e_igual_a_senha_em_texto():
    hash_gerado = Senha.criar(SENHA_FORTE).hash

    assert hash_gerado is not None
    assert hash_gerado != SENHA_FORTE
    assert SENHA_FORTE not in hash_gerado


def test_de_hash_permite_conferir_o_login_depois():
    hash_do_banco = Senha.criar(SENHA_FORTE).hash
    assert hash_do_banco is not None

    senha_lida = Senha.deHash(hash_do_banco)

    assert senha_lida.verificar(SENHA_FORTE) is True


def test_de_hash_nao_valida_forca():
    senha = Senha.deHash("qualquer")

    assert senha.hash == "qualquer"


def test_senha_ausente_nao_tem_hash():
    assert SenhaAusente().hash is None


@pytest.mark.parametrize("tentativa", ["Bolo@2026", "qualquer", "", None], ids=repr)
def test_senha_ausente_recusa_qualquer_tentativa(tentativa):
    assert SenhaAusente().verificar(tentativa) is False


def test_senha_ausente_e_um_tipo_de_senha():
    assert isinstance(SenhaAusente(), Senha)
