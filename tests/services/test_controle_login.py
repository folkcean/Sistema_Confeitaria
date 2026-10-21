from datetime import datetime, timedelta

import pytest

from app.exceptions import AutenticacaoError
from app.services import controle_login
from app.services.controle_login import (
    Bloqueado,
    ControleLogin,
    Livre,
    PoliticaBloqueio,
)

AGORA = datetime(2026, 10, 20, 12, 0)


class RelogioFalso:
    """Relógio de mentira: now() devolve o horário que o teste escolheu"""

    horario = AGORA

    @classmethod
    def now(cls):
        return cls.horario


# Estados
def test_estado_livre_nunca_esta_bloqueado():
    assert Livre().bloqueado(AGORA) is False


def test_livre_continua_livre_antes_do_limite_e_bloqueia_na_falha_que_atinge_o_limite():
    politica = PoliticaBloqueio()

    assert isinstance(Livre(0).aposFalha(politica, AGORA), Livre)
    assert isinstance(Livre(3).aposFalha(politica, AGORA), Livre)
    assert isinstance(Livre(4).aposFalha(politica, AGORA), Bloqueado)


def test_bloqueado_bloqueia_antes_do_fim_e_libera_depois():
    estado = Bloqueado(AGORA + timedelta(minutes=1))

    assert estado.bloqueado(AGORA) is True
    assert estado.bloqueado(AGORA + timedelta(minutes=2)) is False


def test_bloqueado_libera_exatamente_no_horario_final():
    fim = AGORA + timedelta(minutes=1)
    estado = Bloqueado(fim)

    assert estado.bloqueado(fim - timedelta(seconds=1)) is True
    assert estado.bloqueado(fim) is False


def test_falha_depois_do_bloqueio_recomeca_a_contagem_em_livre():
    politica = PoliticaBloqueio(max_tentativas=2)

    estado = Bloqueado(AGORA).aposFalha(politica, AGORA)
    assert isinstance(estado, Livre)

    estado = estado.aposFalha(politica, AGORA)
    assert isinstance(estado, Bloqueado)


@pytest.mark.parametrize(
    "tentativas, estado_esperado",
    [(4, Livre), (5, Bloqueado), (6, Bloqueado)],
    ids=["quatro", "cinco", "seis"],
)
def test_estado_para_escolhe_livre_ou_bloqueado_conforme_as_tentativas(
    tentativas, estado_esperado
):
    estado = PoliticaBloqueio().estadoPara(tentativas, AGORA)

    assert isinstance(estado, estado_esperado)


# ControleLogin
def test_chave_nunca_vista_esta_liberada():
    ControleLogin().exigirLiberado("ana@exemplo.com")


def test_uma_falha_ainda_libera_e_duas_bloqueiam_com_limite_de_duas_tentativas():
    controle = ControleLogin(PoliticaBloqueio(max_tentativas=2))

    controle.registrarFalha("ana@exemplo.com")
    controle.exigirLiberado("ana@exemplo.com")

    controle.registrarFalha("ana@exemplo.com")
    with pytest.raises(AutenticacaoError, match="Muitas tentativas"):
        controle.exigirLiberado("ana@exemplo.com")


def test_limpar_libera_de_novo_e_chave_desconhecida_nao_quebra():
    controle = ControleLogin(PoliticaBloqueio(max_tentativas=1))
    controle.registrarFalha("ana@exemplo.com")

    controle.limpar("ana@exemplo.com")
    controle.exigirLiberado("ana@exemplo.com")

    controle.limpar("nunca-vista@exemplo.com")


def test_chaves_sao_independentes():
    controle = ControleLogin(PoliticaBloqueio(max_tentativas=1))

    controle.registrarFalha("a")

    with pytest.raises(AutenticacaoError):
        controle.exigirLiberado("a")
    controle.exigirLiberado("b")


def test_com_tempo_de_bloqueio_zero_o_bloqueio_vence_na_hora():
    politica = PoliticaBloqueio(max_tentativas=1, tempo_bloqueio=timedelta(0))
    controle = ControleLogin(politica)

    controle.registrarFalha("ana@exemplo.com")

    controle.exigirLiberado("ana@exemplo.com")


# Relógio falso
def test_cinco_falhas_bloqueiam_ate_quinze_minutos_depois(monkeypatch):
    monkeypatch.setattr(controle_login, "datetime", RelogioFalso)
    monkeypatch.setattr(RelogioFalso, "horario", AGORA)
    controle = ControleLogin()

    for _ in range(5):
        controle.registrarFalha("ana@exemplo.com")

    monkeypatch.setattr(RelogioFalso, "horario", AGORA + timedelta(minutes=14))
    with pytest.raises(AutenticacaoError, match="Muitas tentativas"):
        controle.exigirLiberado("ana@exemplo.com")

    monkeypatch.setattr(RelogioFalso, "horario", AGORA + timedelta(minutes=15))
    controle.exigirLiberado("ana@exemplo.com")
