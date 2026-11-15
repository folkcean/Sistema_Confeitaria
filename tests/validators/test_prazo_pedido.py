"""
tests/validators/test_prazo_pedido.py

Testes do validador de prazo (app / validators / prazo_pedido.py)

Como rodar só esse arquivo:   pytest tests/validators/test_prazo_pedido.py -v
"""
from datetime import datetime, time

import pytest

from app.exceptions import ValidacaoError
from app.validators.prazo_pedido import PrazoPedido

CRIACAO = datetime(2026, 11, 2, 10, 0)


# ENCOMENDA
def test_encomenda_exatamente_no_limite_passa():
    PrazoPedido.validarEncomenda(CRIACAO, datetime(2026, 11, 4, 10, 0), 48)


def test_encomenda_um_minuto_antes_do_limite_falha():
    with pytest.raises(ValidacaoError, match="48h de antecedência"):
        PrazoPedido.validarEncomenda(CRIACAO, datetime(2026, 11, 4, 9, 59), 48)


def test_encomenda_mensagem_informa_a_data_minima():
    with pytest.raises(ValidacaoError, match="04/11/2026 10:00"):
        PrazoPedido.validarEncomenda(CRIACAO, datetime(2026, 11, 3, 10, 0), 48)


def test_encomenda_antecedencia_invalida():
    with pytest.raises(ValidacaoError):
        PrazoPedido.validarEncomenda(CRIACAO, datetime(2026, 11, 9, 10, 0), -1)


# PRONTA ENTREGA
def test_pronta_entrega_ate_17h_passa():
    PrazoPedido.validarProntaEntrega(datetime(2026, 11, 2, 17, 0))


def test_pronta_entrega_depois_das_17h_falha():
    with pytest.raises(ValidacaoError, match="até as 17:00"):
        PrazoPedido.validarProntaEntrega(datetime(2026, 11, 2, 17, 1))


def test_pronta_entrega_com_fechamento_diferente():
    PrazoPedido.validarProntaEntrega(datetime(2026, 11, 2, 19, 0), fechamento=time(20, 0))
    with pytest.raises(ValidacaoError):
        PrazoPedido.validarProntaEntrega(datetime(2026, 11, 2, 19, 1), fechamento=time(20, 0))


# PEDIDO INTEIRO
def test_validar_usa_a_maior_antecedencia():
    itens = [(False, 24), (False, 72)]
    PrazoPedido.validar(CRIACAO, datetime(2026, 11, 5, 10, 0), itens)
    with pytest.raises(ValidacaoError, match="72h"):
        PrazoPedido.validar(CRIACAO, datetime(2026, 11, 4, 10, 0), itens)


def test_validar_so_pronta_entrega_nao_exige_antecedencia_de_encomenda():
    PrazoPedido.validar(CRIACAO, datetime(2026, 11, 2, 11, 0), [(True, 48)])


def test_validar_pronta_entrega_fora_do_horario_falha():
    with pytest.raises(ValidacaoError, match="pronta entrega"):
        PrazoPedido.validar(datetime(2026, 11, 2, 17, 30), datetime(2026, 11, 2, 18, 0), [(True, 0)])


def test_validar_misto_confere_os_dois():
    itens = [(True, 0), (False, 48)]
    PrazoPedido.validar(CRIACAO, datetime(2026, 11, 4, 10, 0), itens)
    with pytest.raises(ValidacaoError, match="48h"):
        PrazoPedido.validar(CRIACAO, datetime(2026, 11, 3, 10, 0), itens)


def test_validar_sem_itens_nao_exige_nada():
    PrazoPedido.validar(CRIACAO, datetime(2026, 11, 2, 11, 0), [])


def test_validar_datas_invalidas():
    with pytest.raises(ValidacaoError):
        PrazoPedido.validar(CRIACAO, "amanhã", [(False, 48)])
    with pytest.raises(ValidacaoError):
        PrazoPedido.validar(None, datetime(2026, 11, 9), [(False, 48)])