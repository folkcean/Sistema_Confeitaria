"""
tests / models / test_email_verificado.py

Usuario.email_verificado: nasce falso, é marcado pela confirmação do link e se perde ao trocar o e-mail
(fixtures `cliente` e `outro_cliente` vêm de tests/conftest.py: Ana tem e-mail, Beto não)

COMO RODAR SÓ ESTE ARQUIVO:   pytest tests/models/test_email_verificado.py -v
"""
import pytest

from app.exceptions import ValidacaoError
from app.models.cliente import Cliente


def test_email_nasce_nao_verificado(cliente):
    assert cliente.email_verificado is False


def test_marcar_email_verificado(cliente):
    cliente.marcarEmailVerificado()

    assert cliente.email_verificado is True


def test_pode_nascer_verificado_ao_carregar_do_banco():
    carregado = Cliente("Ana", "ana@exemplo.com", "22999990001", None, email_verificado=True)

    assert carregado.email_verificado is True


def test_sem_email_nao_ha_o_que_confirmar(outro_cliente):
    with pytest.raises(ValidacaoError, match="Cadastre um e-mail"):
        outro_cliente.marcarEmailVerificado()

    assert outro_cliente.email_verificado is False


def test_trocar_o_email_perde_a_confirmacao(cliente):
    cliente.marcarEmailVerificado()

    cliente.email = "ana.nova@exemplo.com"

    assert cliente.email_verificado is False


def test_regravar_o_mesmo_email_mantem_a_confirmacao(cliente):
    cliente.marcarEmailVerificado()

    cliente.email = "ANA@exemplo.com"

    assert cliente.email == "ana@exemplo.com"
    assert cliente.email_verificado is True


def test_apagar_o_email_perde_a_confirmacao(cliente):
    cliente.marcarEmailVerificado()

    cliente.email = None

    assert cliente.email_verificado is False


def test_funciona_nos_tres_perfis(funcionario, administrador):
    funcionario.marcarEmailVerificado()
    administrador.marcarEmailVerificado()

    assert funcionario.email_verificado and administrador.email_verificado