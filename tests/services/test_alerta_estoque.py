"""
tests/services/test_alerta_estoque.py

TESTES DO AlertaEstoque (app/services/alerta_estoque.py).
Farinha: 10 kg, mínimo 3. Leite: 40 latas, mínimo 10.

Como rodar só esse arquivo:   pytest tests/services/test_alerta_estoque.py -v
"""
from decimal import Decimal

from app.services.alerta_estoque import AlertaEstoque


def test_sem_insumos_baixos_nao_ha_alertas(estoque):
    assert AlertaEstoque(estoque).alertas() == []
    assert AlertaEstoque(estoque).listaDeCompras() == []


def test_alerta_quando_chega_ao_minimo(estoque, farinha):
    farinha.registrarConsumo(Decimal("7"))             # sobra 3 = mínimo (a regra usa <=)
    assert AlertaEstoque(estoque).alertas() == ["Farinha: 3.000 kg em estoque (mínimo 3.000 kg)"]


def test_lista_de_compras_traz_quanto_falta(estoque, farinha):
    farinha.registrarConsumo(Decimal("8"))             # sobra 2; faltam 1 para o mínimo
    compras = AlertaEstoque(estoque).listaDeCompras()
    assert [(c["insumo"], c["falta_para_minimo"]) for c in compras] == [("Farinha", Decimal("1.000"))]


def test_novos_alertas_so_dos_insumos_movimentados(estoque, farinha, leite):
    farinha.registrarConsumo(Decimal("8"))             # farinha cai no mínimo ANTES (não movimentada agora)
    mov = leite.registrarConsumo(Decimal("5"))         # leite: 35 > 10, sem alerta
    assert AlertaEstoque(estoque).novosAlertas([mov]) == []


def test_novos_alertas_avisa_o_que_acabou_de_ficar_baixo(estoque, farinha, leite):
    mov_farinha = farinha.registrarConsumo(Decimal("8"))
    mov_leite = leite.registrarConsumo(Decimal("1"))
    alertas = AlertaEstoque(estoque).novosAlertas([mov_farinha, mov_leite])
    assert alertas == ["Farinha: 2.000 kg em estoque (mínimo 3.000 kg)"]


def test_novos_alertas_nao_repete_insumo(estoque, farinha):
    m1 = farinha.registrarConsumo(Decimal("4"))
    m2 = farinha.registrarConsumo(Decimal("4"))
    assert len(AlertaEstoque(estoque).novosAlertas([m1, m2])) == 1