"""
tests/services/test_alerta_estoque.py

TESTES DO AlertaEstoque (app/services/alerta_estoque.py).
Farinha: 10000 g, mínimo 3000 g. Leite: 15800 g (40 latas), mínimo 3950 g (10 latas).
O saldo fica na unidade da receita (g).

Como rodar só esse arquivo:   pytest tests/services/test_alerta_estoque.py -v
"""
from decimal import Decimal

from app.services.alerta_estoque import AlertaEstoque


def test_sem_insumos_baixos_nao_ha_alertas(estoque):
    assert AlertaEstoque(estoque).alertas() == []
    assert AlertaEstoque(estoque).listaDeCompras() == []


def test_alerta_quando_chega_ao_minimo(estoque, farinha):
    farinha.registrarConsumo(Decimal("7000"))          # sobra 3000 g = mínimo (a regra usa <=)
    assert AlertaEstoque(estoque).alertas() == ["Farinha: 3000.000 g em estoque (mínimo 3000.000 g)"]


def test_lista_de_compras_traz_quanto_falta(estoque, farinha):
    farinha.registrarConsumo(Decimal("8000"))          # sobra 2000 g; faltam 1000 g para o mínimo
    compras = AlertaEstoque(estoque).listaDeCompras()
    assert [(c["insumo"], c["falta_para_minimo"], c["unidade"]) for c in compras] == [("Farinha", Decimal("1000"), "g")]


def test_novos_alertas_so_dos_insumos_movimentados(estoque, farinha, leite):
    farinha.registrarConsumo(Decimal("8000"))          # farinha cai no mínimo ANTES (não movimentada agora)
    mov = leite.registrarConsumo(Decimal("1975"))      # leite: 13825 g > 3950 g, sem alerta
    assert AlertaEstoque(estoque).novosAlertas([mov]) == []


def test_novos_alertas_avisa_o_que_acabou_de_ficar_baixo(estoque, farinha, leite):
    mov_farinha = farinha.registrarConsumo(Decimal("8000"))
    mov_leite = leite.registrarConsumo(Decimal("395"))
    alertas = AlertaEstoque(estoque).novosAlertas([mov_farinha, mov_leite])
    assert alertas == ["Farinha: 2000.000 g em estoque (mínimo 3000.000 g)"]


def test_novos_alertas_nao_repete_insumo(estoque, farinha):
    m1 = farinha.registrarConsumo(Decimal("4000"))
    m2 = farinha.registrarConsumo(Decimal("4000"))
    assert len(AlertaEstoque(estoque).novosAlertas([m1, m2])) == 1