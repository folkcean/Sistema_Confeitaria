import re
from dataclasses import FrozenInstanceError

import pytest

from app.exceptions import SenhaFracaError, ValidacaoError
from app.validators.senha import RegraSenha, ValidadorSenha

REGRA_TAMANHO = "ter entre 8 e 128 caracteres"
REGRA_LETRAS = "conter letras"
REGRA_NUMEROS = "conter números"
REGRA_ESPECIAL = "conter ao menos um caractere especial (ex.: @, #, !)"


def test_regra_senha_violada_quando_padrao_nao_casa():
    regra = RegraSenha("conter numeros", re.compile(r"\d"))

    assert regra.violada("abc") is True
    assert regra.violada("a1") is False


def test_regra_senha_e_imutavel():
    regra = RegraSenha("conter numeros", re.compile(r"\d"))

    with pytest.raises(FrozenInstanceError):
        regra.descricao = "x"  # type: ignore


# Testes de Validar senha.
def mensagem_de(senha):
    """Roda o validador, exige que dê erro e devolve a mensagem"""
    with pytest.raises(SenhaFracaError) as info:
        ValidadorSenha.validar(senha)
    return str(info.value)


def test_senha_forte_passa_sem_erro():
    assert ValidadorSenha.validar("Bolo@2026") is None


@pytest.mark.parametrize(
    "senha, regra_quebrada",
    [
        ("Bo@2026", REGRA_TAMANHO),
        ("12345678@", REGRA_LETRAS),
        ("Bolo@abcd", REGRA_NUMEROS),
        ("Bolo2026x", REGRA_ESPECIAL),
    ],
    ids=["curta", "sem_letra", "sem_numero", "sem_especial"],
)
def test_senha_com_uma_regra_quebrada_cita_so_essa_regra(senha, regra_quebrada):
    assert mensagem_de(senha) == f"A senha deve {regra_quebrada}."


def test_senha_com_128_caracteres_e_aceita():
    senha = "a1@" + "a" * 125

    assert len(senha) == 128
    assert ValidadorSenha.validar(senha) is None


def test_senha_com_129_caracteres_levanta_erro_de_tamanho():
    senha = "a1@" + "a" * 126

    assert len(senha) == 129
    assert REGRA_TAMANHO in mensagem_de(senha)


def test_senha_vazia_lista_as_quatro_regras():
    mensagem = mensagem_de("")

    assert REGRA_TAMANHO in mensagem
    assert REGRA_LETRAS in mensagem
    assert REGRA_NUMEROS in mensagem
    assert REGRA_ESPECIAL in mensagem


def test_senha_none_se_comporta_como_vazia():
    assert mensagem_de(None) == mensagem_de("")


def test_senha_fraca_levanta_erro_que_e_um_validacao_error():
    with pytest.raises(SenhaFracaError):
        ValidadorSenha.validar("abc")

    assert issubclass(SenhaFracaError, ValidacaoError)


@pytest.mark.parametrize("senha", ["senha ok1", "açãoçãoç1"], ids=repr)
def test_espaco_e_letra_acentuada_contam_como_caractere_especial(senha):
    assert ValidadorSenha.validar(senha) is None
