"""
tests/models/test_movimentacao_estoque.py

Testes de MovimentacaoEstoque e das regras do TipoMovimentacao.
"""
from decimal import Decimal

import pytest

from app.exceptions import ValidacaoError
from app.models import MovimentacaoEstoque, TipoMovimentacao


def test_variacao_depende_do_tipo():
    assert TipoMovimentacao.ENTRADA.variacao(Decimal("5")) == 5
    assert TipoMovimentacao.CONSUMO.variacao(Decimal("2")) == -2
    assert TipoMovimentacao.PERDA.variacao(Decimal("1")) == -1
    assert TipoMovimentacao.AJUSTE.variacao(Decimal("-3")) == -3


def test_so_perda_e_ajuste_exigem_motivo():
    assert TipoMovimentacao.PERDA.exigeMotivo() and TipoMovimentacao.AJUSTE.exigeMotivo()
    assert not TipoMovimentacao.ENTRADA.exigeMotivo() and not TipoMovimentacao.CONSUMO.exigeMotivo()


def test_pedido_so_em_consumo_e_compra_so_em_entrada(farinha):
    with pytest.raises(ValidacaoError):
        MovimentacaoEstoque(farinha, TipoMovimentacao.ENTRADA, 1, id_pedido=3)
    with pytest.raises(ValidacaoError):
        MovimentacaoEstoque(farinha, TipoMovimentacao.CONSUMO, 1, id_compra=3)
    assert MovimentacaoEstoque(farinha, TipoMovimentacao.CONSUMO, 1, id_pedido=3).id_pedido == 3


def test_consumo_nao_aceita_quantidade_negativa(farinha):
    with pytest.raises(ValidacaoError):
        MovimentacaoEstoque(farinha, TipoMovimentacao.CONSUMO, -1)


def test_tipo_invalido_e_recusado(farinha):
    with pytest.raises(ValidacaoError):
        MovimentacaoEstoque(farinha, "inexistente", 1)